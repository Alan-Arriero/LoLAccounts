const state={accounts:[],query:'',tier:'ALL',sort:'name'};
const $=s=>document.querySelector(s);
const tiers=['IRON','BRONZE','SILVER','GOLD','PLATINUM','EMERALD','DIAMOND','MASTER','GRANDMASTER','CHALLENGER'];
const labels={IRON:'Hierro',BRONZE:'Bronce',SILVER:'Plata',GOLD:'Oro',PLATINUM:'Platino',EMERALD:'Esmeralda',DIAMOND:'Diamante',MASTER:'Maestro',GRANDMASTER:'Gran maestro',CHALLENGER:'Retador',UNRANKED:'Sin clasificar'};
const api=async(path,options={})=>{const r=await fetch(path,{headers:{'Content-Type':'application/json',...(options.headers||{})},...options});if(!r.ok){let m='Algo salió mal.';try{m=(await r.json()).detail||m}catch{}throw Error(m)}return r.status===204?null:r.json()};
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function toast(m){const e=$('#toast');e.textContent=m;e.classList.add('visible');clearTimeout(toast.timer);toast.timer=setTimeout(()=>e.classList.remove('visible'),2800)}
function openModal(id,backdrop='#modal-backdrop'){const bg=$(backdrop);bg.classList.add('open');bg.setAttribute('aria-hidden','false');bg.querySelectorAll('.modal').forEach(m=>m.classList.remove('active'));$(id).classList.add('active');setTimeout(()=>$(id+' input')?.focus(),70)}
function closeModal(backdrop){if(!backdrop)return;backdrop.classList.remove('open');backdrop.setAttribute('aria-hidden','true')}
function tier(a){return a.tier&&tiers.includes(a.tier)?a.tier:'UNRANKED'}
function tierLabel(a){return labels[tier(a)]+(a.rank?' '+a.rank:'')}
function ti(a){return tiers.indexOf(tier(a))}
const divisions=['IV','III','II','I'];
function nextDivision(a){
  const currentTier=tier(a),tierIndex=tiers.indexOf(currentTier),rank=String(a.rank||'').toUpperCase(),divisionIndex=divisions.indexOf(rank);
  if(tierIndex<0||tierIndex>6||divisionIndex<0)return '';
  if(divisionIndex<divisions.length-1)return labels[currentTier]+' '+divisions[divisionIndex+1];
  const nextTier=tiers[tierIndex+1];
  return nextTier==='MASTER'?labels.MASTER:nextTier?labels[nextTier]+' IV':'';
}
function rankProgress(a){
  const target=nextDivision(a);
  if(!target)return '';
  const raw=Number(a.league_points)||0,lp=Math.max(0,Math.min(100,raw)),shown=Math.round(lp),remaining=Math.max(0,100-shown);
  const message=remaining===0?'PROMOCIÓN DISPONIBLE':'FALTAN '+remaining+' LP PARA '+target.toUpperCase();
  return '<div class="rank-progress"><div class="rank-progress-label"><span>'+shown+' / 100 LP</span><small>'+esc(message)+'</small></div><div class="rank-progress-track" role="progressbar" aria-label="Progreso hacia '+esc(target)+'" aria-valuemin="0" aria-valuemax="100" aria-valuenow="'+shown+'"><span style="width:'+lp+'%"></span></div></div>';
}
function renderFilters(){const n=Object.fromEntries([...tiers,'UNRANKED'].map(t=>[t,0]));state.accounts.forEach(a=>n[tier(a)]++);const rows=[['ALL','Mostrar todas las cuentas','all.svg'],...tiers.map(t=>[t,labels[t],t.toLowerCase()+'.png']),['UNRANKED',labels.UNRANKED,'unranked.svg']];$('#rank-filters').innerHTML=rows.map(r=>'<button class="rank-filter '+(state.tier===r[0]?'selected':'')+'" data-tier="'+r[0]+'" title="'+esc(r[1])+'" '+(r[0]==='ALL'?'aria-label="Mostrar todas las cuentas"':'')+'><img src="/static/ranks/'+r[2]+'" alt="">'+(r[0]==='ALL'?'':'<span>'+esc(r[1])+'</span>')+'<b>'+(r[0]==='ALL'?state.accounts.length:n[r[0]])+'</b></button>').join('')}
function card(a){
  const total=(a.wins||0)+(a.losses||0),wr=total?Math.round(a.wins*100/total):0,u=tier(a)==='UNRANKED',slug=u?'unranked':tier(a).toLowerCase();
  const name=String(a.game_name||'').trim(),tag=String(a.tag_line||'').trim(),hasId=Boolean(a.has_riot_id&&name&&tag);
  const icon=a.profile_icon_id&&a.icon_version?'<img class="profile-icon" src="https://ddragon.leagueoflegends.com/cdn/'+encodeURIComponent(a.icon_version)+'/img/profileicon/'+a.profile_icon_id+'.png" alt="Icono de perfil de '+esc(name)+'">':'<div class="profile-icon profile-icon-empty" aria-hidden="true"></div>';
  const identity='<div class="account-id-line"><span class="account-name">'+esc(name)+'</span>'+(hasId?'<span class="account-tag">#'+esc(tag)+'</span>':'')+'</div>'+(hasId?'<button class="copy-id" data-copy-account-id="'+Number(a.id)+'">▣ COPIAR RIOT ID</button>':'<button class="link-riot-id" data-edit-riot="'+Number(a.id)+'">＋ VINCULAR RIOT ID</button>');
  return '<article class="account-card"><div class="card-top"><div class="account-identity">'+identity+'</div>'+icon+'<button class="card-menu" data-menu="'+Number(a.id)+'" aria-label="Opciones de cuenta">⋯</button><div class="account-menu" id="menu-'+Number(a.id)+'" hidden><button data-refresh="'+Number(a.id)+'">↻ Actualizar rango</button><button data-edit-riot="'+Number(a.id)+'">✎ Editar Riot ID</button><button data-label="'+Number(a.id)+'">✎ Editar etiqueta</button><button data-delete="'+Number(a.id)+'">⌫ Eliminar cuenta</button></div></div>'+(a.label?'<div class="account-label">'+esc(a.label)+'</div>':'')+'<div class="rank-row"><img class="rank-emblem-image" src="/static/ranks/'+slug+(u?'.svg':'.png')+'" alt="Emblema de '+esc(labels[tier(a)])+'"><div class="rank-text"><b class="'+(u?'unranked':'')+'">'+esc(tierLabel(a))+'</b><small>'+(u?'SIN CLASIFICAR':'RANKED SOLO/DUO')+'</small></div></div>'+(!u&&hasId?rankProgress(a):'')+'<div class="card-footer"><span class="win-rate">'+(total?'<b>'+wr+'%</b> WR · '+a.wins+'V / '+a.losses+'D':'Sin partidas clasificatorias')+'</span><div class="card-actions"><button class="login-btn" data-login="'+Number(a.id)+'">INICIAR SESIÓN</button></div></div></article>'
}
function render(){const all=state.accounts;$('#heading-count').textContent='('+String(all.length).padStart(2,'0')+')';renderFilters();let list=all.filter(a=>(state.tier==='ALL'||tier(a)===state.tier)&&((a.game_name||'')+' '+(a.tag_line||'')+' '+(a.label||'')).toLowerCase().includes(state.query));if(state.sort==='rank')list.sort((a,b)=>ti(b)-ti(a)||(b.league_points||0)-(a.league_points||0)||(a.game_name||'').localeCompare(b.game_name||''));else if(state.sort==='winrate')list.sort((a,b)=>{const x=(a.wins||0)+(a.losses||0),y=(b.wins||0)+(b.losses||0);return(y?(b.wins||0)/y:0)-(x?(a.wins||0)/x:0)});else list.sort((a,b)=>(a.game_name||'').localeCompare(b.game_name||''));$('#accounts').innerHTML=list.map(card).join('');$('#accounts').style.display=list.length?'grid':'none';$('#empty-state').classList.toggle('visible',all.length===0);let empty=$('#filter-empty');if(!empty){empty=document.createElement('div');empty.id='filter-empty';empty.className='empty-state';empty.innerHTML='<div class="empty-symbol">⌕</div><h3>No hay cuentas con esos filtros</h3><p>Cambia el elo seleccionado o prueba otro nombre.</p><button class="clear-filters lol-button">MOSTRAR TODAS</button>';$('.collection').insertBefore(empty,$('footer'))}empty.classList.toggle('visible',all.length>0&&!list.length)}
async function load(){try{state.accounts=await api('/api/accounts');render()}catch(e){toast(e.message)}}
function error(text,id='#form-error'){const el=$(id);el.textContent=text;el.classList.add('visible')}
function clearError(id='#form-error'){const el=$(id);el.textContent='';el.classList.remove('visible')}
function setLoginStep(id,status){const el=$(id);el.classList.remove('active','complete','failed');if(status)el.classList.add(status)}
function paintLoginStatus(s){
  const step=s.step||'client',terminal=['success','error'].includes(s.state);
  const order=['client','signout','credentials','typing','verification','launch','success'];
  const current=order.indexOf(step);
  const done=s.state==='success'?3:Math.max(0,Math.min(3,current>=5?2:current>=2?1:0));
  ['#login-step-client','#login-step-credentials','#login-step-league'].forEach((selector,index)=>{
    const status=s.state==='success'||index<done?'complete':index===done&&!terminal?'active':'';
    setLoginStep(selector,status);
  });
  if(s.state==='error')setLoginStep(step==='launch'?'#login-step-league':step==='typing'||step==='verification'?'#login-step-credentials':'#login-step-client','failed');
  $('#login-description').textContent=s.state==='success'?'Riot confirmó el inicio de sesión.':s.state==='error'?'No se pudo completar el inicio de sesión.':'Iniciando sesión automáticamente…';
  $('#login-live-status').textContent=s.message||'Procesando…';
  $('#login-close-app').hidden=s.state!=='success';
}
async function pollLoginStatus(id){
  try{
    const status=await api('/api/accounts/'+id+'/login-status');
    paintLoginStatus(status);
    if(['starting','running','verification'].includes(status.state))setTimeout(()=>pollLoginStatus(id),500);
  }catch(e){paintLoginStatus({state:'error',step:'error',message:e.message})}
}
async function beginLogin(id){
  const account=state.accounts.find(a=>a.id===Number(id));
  $('#login-account-name').textContent=(account?.game_name||'CUENTA')+(account?.has_riot_id?'#'+account.tag_line:'');
  $('#login-description').textContent='Iniciando sesión automáticamente…';
  $('#login-live-status').textContent='Abriendo Riot Client…';
  $('#login-close-app').hidden=true;
  for(const step of ['#login-step-client','#login-step-credentials','#login-step-league'])setLoginStep(step,'');
  setLoginStep('#login-step-client','active');
  openModal('#login-modal','#login-backdrop');
  try{await api('/api/accounts/'+id+'/login',{method:'POST'});pollLoginStatus(id)}
  catch(e){paintLoginStatus({state:'error',step:'client',message:e.message})}
}
function editRiotId(id){const account=state.accounts.find(a=>a.id===Number(id));if(!account)return;state.editingAccountId=Number(id);$('#edit-riot-name').value=account.has_riot_id?account.game_name:'';$('#edit-riot-tag').value=account.has_riot_id?account.tag_line:'';clearError('#riot-id-error');$('#riot-id-submit-text').textContent='CONSULTAR Y VINCULAR';openModal('#riot-id-modal','#riot-id-backdrop')}
async function copyRiotId(value){try{await navigator.clipboard.writeText(value);toast('Riot ID copiado: '+value)}catch{const input=document.createElement('textarea');input.value=value;input.style.position='fixed';input.style.opacity='0';document.body.appendChild(input);input.select();const ok=document.execCommand('copy');input.remove();toast(ok?'Riot ID copiado: '+value:'No se pudo copiar el Riot ID')}}
document.addEventListener('click',async e=>{const target=e.target,backdrop=target.closest('.modal-backdrop');if(target.closest('[data-close]')){closeModal(backdrop);return}const tierButton=target.closest('[data-tier]');if(tierButton){state.tier=tierButton.dataset.tier;render();return}if(target.closest('.clear-filters')){state.tier='ALL';state.query='';$('#search').value='';render();return}if(target.closest('#add-open,#empty-add')){clearError();$('#add-form').reset();openModal('#account-modal');return}if(target===$('#modal-backdrop')||target===$('#riot-id-backdrop')||target===$('#login-backdrop')){closeModal(target);return}if(target.closest('[data-menu]')){const id=target.closest('[data-menu]').dataset.menu;document.querySelectorAll('.account-menu').forEach(m=>m.hidden=true);$('#menu-'+id).hidden=false;return}if(target.closest('[data-edit-riot]')){editRiotId(target.closest('[data-edit-riot]').dataset.editRiot);return}if(target.closest('[data-copy-account-id]')){const id=Number(target.closest('[data-copy-account-id]').dataset.copyAccountId),account=state.accounts.find(item=>Number(item.id)===id);if(!account?.has_riot_id||!account.game_name||!account.tag_line){toast('Esta cuenta no tiene Riot ID para copiar');return}await copyRiotId(String(account.game_name).trim()+'#'+String(account.tag_line).trim());return}if(target.closest('[data-login]')){await beginLogin(target.closest('[data-login]').dataset.login);return}if(target.closest('[data-delete]')){const id=target.closest('[data-delete]').dataset.delete;if(confirm('¿Eliminar esta cuenta de tu colección?'))try{await api('/api/accounts/'+id,{method:'DELETE'});await load();toast('Cuenta eliminada')}catch(x){toast(x.message)}return}if(target.closest('[data-refresh]')){const id=target.closest('[data-refresh]').dataset.refresh;try{const a=await api('/api/accounts/'+id+'/refresh',{method:'POST'});state.accounts=state.accounts.map(x=>x.id===a.id?a:x);render();toast('Rango actualizado desde Riot')}catch(x){toast(x.message)}return}if(target.closest('[data-label]')){const id=target.closest('[data-label]').dataset.label,a=state.accounts.find(x=>x.id===Number(id)),label=prompt('Etiqueta de la cuenta (opcional):',a?.label||'');if(label!==null)try{const x=await api('/api/accounts/'+id,{method:'PATCH',body:JSON.stringify({label})});state.accounts=state.accounts.map(y=>y.id===x.id?x:y);render()}catch(x){toast(x.message)}return}if(!target.closest('.account-menu'))document.querySelectorAll('.account-menu').forEach(m=>m.hidden=true)});
$('#add-form').addEventListener('submit',async e=>{e.preventDefault();clearError();const form=e.currentTarget,data=Object.fromEntries(new FormData(form)),button=form.querySelector('button[type=submit]'),text=$('#submit-text'),hasRiotId=Boolean(data.game_name.trim()||data.tag_line.trim());button.disabled=true;text.textContent=hasRiotId?'CONSULTANDO RIOT…':'AÑADIENDO CUENTA…';try{const account=await api('/api/accounts',{method:'POST',body:JSON.stringify(data)});state.accounts.push(account);render();closeModal($('#modal-backdrop'));form.reset();toast('Cuenta '+account.game_name+' añadida')}catch(x){error(x.message)}finally{button.disabled=false;text.textContent='BUSCAR Y AÑADIR CUENTA'}});
$('#riot-id-form').addEventListener('submit',async e=>{e.preventDefault();clearError('#riot-id-error');const form=e.currentTarget,data=Object.fromEntries(new FormData(form)),id=state.editingAccountId,button=form.querySelector('button[type=submit]'),text=$('#riot-id-submit-text');button.disabled=true;text.textContent='CONSULTANDO RIOT…';try{const account=await api('/api/accounts/'+id,{method:'PATCH',body:JSON.stringify(data)});state.accounts=state.accounts.map(a=>a.id===account.id?account:a);render();closeModal($('#riot-id-backdrop'));toast('Riot ID vinculado y rango actualizado')}catch(x){error(x.message,'#riot-id-error')}finally{button.disabled=false;text.textContent='CONSULTAR Y VINCULAR'}});
$('#search').addEventListener('input',e=>{state.query=e.target.value.trim().toLowerCase();render()});$('#sort-select').addEventListener('change',e=>{state.sort=e.target.value;render()});$('#login-close-app').addEventListener('click',async()=>{try{await api('/api/app/close',{method:'POST'})}catch(e){toast(e.message)}});document.addEventListener('keydown',e=>{if(e.key==='Escape')document.querySelectorAll('.modal-backdrop.open').forEach(closeModal);if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();$('#search').focus()}});load();
