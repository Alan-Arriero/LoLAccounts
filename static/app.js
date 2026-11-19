const state={accounts:[],query:'',tier:'ALL',sort:'name',playWithQueue:'solo',playWithTier:null,settings:{close_after_login:false,launch_on_windows:false,launch_minimized:false,language:'es',accounts_per_row:3},loginAccountId:null,lastLoginCloseId:null,lastRankRefresh:null,refreshSeconds:3600,refreshing:false};
const $=s=>document.querySelector(s);
const loginStepIds=['#login-step-client','#login-step-wait','#login-step-signout','#login-step-connect','#login-step-find','#login-step-credentials','#login-step-verification','#login-step-league'];
const tiers=['IRON','BRONZE','SILVER','GOLD','PLATINUM','EMERALD','DIAMOND','MASTER','GRANDMASTER','CHALLENGER'];
const rankNames={es:{IRON:'Hierro',BRONZE:'Bronce',SILVER:'Plata',GOLD:'Oro',PLATINUM:'Platino',EMERALD:'Esmeralda',DIAMOND:'Diamante',MASTER:'Maestro',GRANDMASTER:'Gran maestro',CHALLENGER:'Retador',UNRANKED:'Sin clasificar'},en:{IRON:'Iron',BRONZE:'Bronze',SILVER:'Silver',GOLD:'Gold',PLATINUM:'Platinum',EMERALD:'Emerald',DIAMOND:'Diamond',MASTER:'Master',GRANDMASTER:'Grandmaster',CHALLENGER:'Challenger',UNRANKED:'Unranked'}};
const messages={es:{filter:'FILTRAR POR ELO',all:'Todas',accounts:'CUENTAS',sortName:'Nombre A–Z',sortRank:'Rango',sortWinrate:'Porcentaje de victorias',search:'Buscar cuenta...',addAccount:'AÑADIR CUENTA',emptyTitle:'Aún no hay cuentas',emptyText:'Añade una cuenta EUW con tu Riot ID para consultar su rango.',addFirst:'AÑADIR PRIMERA CUENTA',footer:'RIOT GAMES NO ENDORSA NI PATROCINA ESTA APLICACIÓN.',newAccount:'NUEVA CUENTA',addDescription:'Añade el Riot ID ahora o vincúlalo más tarde para consultar el rango. Los dos campos son opcionales.',summonerName:'Nombre de invocador',username:'USUARIO O EMAIL DE RIOT',usernamePlaceholder:'Tu usuario de acceso',password:'CONTRASEÑA',passwordPlaceholder:'Contraseña de Riot',profileHint:'El Riot ID identifica el perfil; el usuario y contraseña sirven para iniciar sesión.',label:'ETIQUETA',optional:'OPCIONAL',credentialNote:'El acceso se guarda en el Administrador de credenciales de Windows.',addSubmit:'BUSCAR Y AÑADIR CUENTA',linkTitle:'VINCULAR CUENTA',linkDescription:'Escribe el Riot ID para consultar el rango de esta cuenta en EUW.',name:'NOMBRE',tag:'TAG',linkSubmit:'CONSULTAR Y VINCULAR',preferences:'PREFERENCIAS',settings:'Ajustes',settingsDescription:'Personaliza cómo se comporta Rift Vault.',closeAfterLogin:'Cerrar Rift Vault al iniciar sesión',closeAfterLoginHelp:'Cierra la app cuando League se haya abierto con la cuenta elegida.',launchWindows:'Abrir Rift Vault con Windows',launchWindowsHelp:'Inicia la app automáticamente al entrar en Windows.',language:'Idioma de la interfaz',saveSettings:'GUARDAR AJUSTES',settingsSaved:'Ajustes guardados',loginKicker:'INICIO DE SESIÓN',loginDescription:'Iniciando sesión automáticamente…',stepClient:'Abrir Riot Client',stepClientHelp:'Preparando el cliente de Riot',stepSwitch:'Cambiar de cuenta',stepSwitchHelp:'Cerrando la sesión anterior si hace falta',stepCredentials:'Introducir credenciales',stepCredentialsHelp:'Usando los datos guardados de forma segura',stepVerify:'Verificar acceso',stepVerifyHelp:'Confirmando la cuenta con Riot',stepLeague:'Abrir League of Legends',stepLeagueHelp:'Iniciando el juego con la cuenta elegida',back:'Volver',progressLabel:'Progreso de actualización de League of Legends',riotUpdating:'Riot está actualizando League of Legends',allGames:'Sin partidas clasificatorias',soloRanked:'CLASIFICATORIA SOLO/DUO',unrankedLabel:'SIN CLASIFICAR',copy:'▣ COPIAR RIOT ID',link:'＋ VINCULAR RIOT ID',login:'INICIAR SESIÓN',refresh:'↻ Actualizar rango',editRiot:'✎ Editar Riot ID',editLabel:'✎ Editar etiqueta',deleteAccount:'⌫ Eliminar cuenta',refreshTimer:'ACTUALIZACIÓN EN',refreshing:'ACTUALIZANDO RANGOS',updating:'Riot está actualizando League of Legends',process:'Procesando…',copied:'Riot ID copiado: ',copyFailed:'No se pudo copiar el Riot ID',noRiotId:'Esta cuenta no tiene un Riot ID vinculado',noFilterTitle:'No hay cuentas con esos filtros',noFilterText:'Cambia el elo seleccionado o prueba otro nombre.',showAll:'MOSTRAR TODAS',main:'Main, Smurf, Flex...',updatingRange:'Actualizando rango desde Riot',rankUpdated:'Rango actualizado desde Riot',linked:'Riot ID vinculado y rango actualizado',added:' añadida',enterLabel:'Etiqueta de la cuenta (opcional):'},en:{filter:'FILTER BY RANK',all:'All',accounts:'ACCOUNTS',sortName:'Name A–Z',sortRank:'Rank',sortWinrate:'Win rate',search:'Search accounts...',addAccount:'ADD ACCOUNT',emptyTitle:'No accounts yet',emptyText:'Add an EUW account with a Riot ID to view its rank.',addFirst:'ADD YOUR FIRST ACCOUNT',footer:'RIOT GAMES DOES NOT ENDORSE OR SPONSOR THIS APP.',newAccount:'NEW ACCOUNT',addDescription:'Add a Riot ID now or link it later to view the rank. Both fields are optional.',summonerName:'Summoner name',username:'RIOT USERNAME OR EMAIL',usernamePlaceholder:'Your sign-in username',password:'PASSWORD',passwordPlaceholder:'Riot password',profileHint:'The Riot ID identifies the profile; username and password are used to sign in.',label:'LABEL',optional:'OPTIONAL',credentialNote:'Credentials are stored in Windows Credential Manager.',addSubmit:'LOOK UP AND ADD ACCOUNT',linkTitle:'LINK ACCOUNT',linkDescription:'Enter the Riot ID to look up this account’s EUW rank.',name:'NAME',tag:'TAG',linkSubmit:'LOOK UP AND LINK',preferences:'PREFERENCES',settings:'Settings',settingsDescription:'Choose how Rift Vault behaves.',closeAfterLogin:'Close Rift Vault after sign-in',closeAfterLoginHelp:'Close the app after League opens with the selected account.',launchWindows:'Launch Rift Vault with Windows',launchWindowsHelp:'Start the app automatically when you sign in to Windows.',language:'Interface language',saveSettings:'SAVE SETTINGS',settingsSaved:'Settings saved',loginKicker:'SIGNING IN',loginDescription:'Signing in automatically…',stepClient:'Open Riot Client',stepClientHelp:'Preparing Riot Client',stepSwitch:'Switch account',stepSwitchHelp:'Signing out of the previous account if needed',stepCredentials:'Enter credentials',stepCredentialsHelp:'Using the saved credentials securely',stepVerify:'Verify access',stepVerifyHelp:'Confirming the account with Riot',stepLeague:'Open League of Legends',stepLeagueHelp:'Starting the game with the selected account',back:'Back',progressLabel:'League of Legends update progress',riotUpdating:'Riot is updating League of Legends',allGames:'No ranked games',soloRanked:'RANKED SOLO/DUO',unrankedLabel:'UNRANKED',copy:'▣ COPY RIOT ID',link:'＋ LINK RIOT ID',login:'SIGN IN',refresh:'↻ Refresh rank',editRiot:'✎ Edit Riot ID',editLabel:'✎ Edit label',deleteAccount:'⌫ Delete account',refreshTimer:'RANKS UPDATE IN',refreshing:'UPDATING RANKS',updating:'Riot is updating League of Legends',process:'Working…',copied:'Riot ID copied: ',copyFailed:'Could not copy Riot ID',noRiotId:'This account has no linked Riot ID',noFilterTitle:'No accounts match these filters',noFilterText:'Change the selected rank or try another name.',showAll:'SHOW ALL',main:'Main, Smurf, Flex...',updatingRange:'Updating rank from Riot',rankUpdated:'Rank updated from Riot',linked:'Riot ID linked and rank updated',added:' added',enterLabel:'Account label (optional):'}};
Object.assign(messages.es,{copyPassword:'▣ COPIAR CONTRASEÑA',passwordCopied:'Contraseña copiada al portapapeles',passwordCopyFailed:'No se pudo copiar la contraseña',launchMinimized:'Iniciar minimizado',launchMinimizedHelp:'Iniciar Rift Vault con la ventana minimizada.',loginSuccess:'Has iniciado sesión con esta cuenta',rankUnranked:'Sin clasificar'});
Object.assign(messages.en,{copyPassword:'▣ COPY PASSWORD',passwordCopied:'Password copied to clipboard',passwordCopyFailed:'Could not copy the password',launchMinimized:'Start minimized',launchMinimizedHelp:'Start Rift Vault with its window minimized.',loginSuccess:'You have signed in with this account',rankUnranked:'Unranked'});
Object.assign(messages.es,{copy:'Copiar Riot ID',copyPassword:'Copiar contraseña',login:'INICIAR SESIÓN',sortRank:'Rango descendente',sortRankAsc:'Rango ascendente'});
Object.assign(messages.en,{copy:'Copy Riot ID',copyPassword:'Copy password',login:'SIGN IN',sortRank:'Rank descending',sortRankAsc:'Rank ascending'});
const playWithMessages={es:{playWith:'Puede jugar con',playWithTitle:'PUEDE JUGAR CON',queueSolo:'Solo/Duo',queueFlex:'Flex',clearPlayWith:'Quitar filtro',soloRulesNote:'Compatibilidad estimada según rango visible. El MMR oculto puede imponer límites adicionales.',flexRulesNote:'En Flex no hay restricciones de rango hasta Diamante; para jugar con Maestro o superior se necesita Esmeralda.',flexRanked:'CLASIFICATORIA FLEX'},en:{playWith:'Can play with',playWithTitle:'CAN PLAY WITH',queueSolo:'Solo/Duo',queueFlex:'Flex',clearPlayWith:'Clear filter',soloRulesNote:'Estimated from visible rank. Hidden MMR may add restrictions.',flexRulesNote:'Flex has no rank restrictions through Diamond; playing with Master or above requires Emerald.',flexRanked:'RANKED FLEX'}};
const tr=key=>(playWithMessages[state.settings.language||'es']||playWithMessages.es)[key]||(messages[state.settings.language||'es']||messages.es)[key]||messages.es[key]||key;
const tierName=key=>(rankNames[state.settings.language||'es']||rankNames.es)[key]||key;
const api=async(path,options={})=>{const r=await fetch(path,{headers:{'Content-Type':'application/json',...(options.headers||{})},...options});if(!r.ok){let m='Algo salió mal.';try{m=(await r.json()).detail||m}catch{}throw Error(m)}return r.status===204?null:r.json()};
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function localize(message){if(state.settings.language!=='en')return String(message);const pairs=[['Cuenta no encontrada','Account not found'],['Esta cuenta no tiene credenciales guardadas','This account has no saved credentials'],['La cuenta no tiene usuario y contraseña guardados','This account has no saved username and password'],['Configura RIOT_API_KEY en el archivo .env','Set RIOT_API_KEY in the .env file'],['Completa el Riot ID y el tag','Enter both the Riot ID and tag'],['Añade el Riot ID y tag antes de actualizar el rango','Link a Riot ID and tag before refreshing the rank'],['Riot Client no permitió cerrar la sesión anterior','Riot Client could not sign out of the previous account'],['Riot no confirmó el acceso a tiempo','Riot did not confirm sign-in in time'],['Riot rechazó abrir League of Legends','Riot refused to launch League of Legends'],['No se pudo cerrar League of Legends','League of Legends could not be closed'],['Windows no pudo guardar la contraseña en su almacén seguro','Windows could not save the password to its secure credential store']];for(const [es,en] of pairs)if(String(message).includes(es))return String(message).replace(es,en);return String(message)}
function toast(m){const e=$('#toast');e.textContent=localize(m);e.classList.add('visible');clearTimeout(toast.timer);toast.timer=setTimeout(()=>e.classList.remove('visible'),2800)}
function openModal(id,backdrop='#modal-backdrop'){const bg=$(backdrop);bg.classList.add('open');bg.setAttribute('aria-hidden','false');bg.querySelectorAll('.modal').forEach(m=>m.classList.remove('active'));$(id).classList.add('active');setTimeout(()=>$(id+' input')?.focus(),70)}
function closeModal(backdrop){if(!backdrop)return;backdrop.classList.remove('open');backdrop.setAttribute('aria-hidden','true')}
function applyLanguage(){
  const en=state.settings.language==='en';document.documentElement.lang=en?'en':'es';try{localStorage.setItem('rift-vault-language',en?'en':'es')}catch{}
  $('.rank-title').textContent=tr('filter');$('.section-heading h2').childNodes[0].textContent=tr('accounts')+' ';$('#sort-select').options[0].text=tr('sortName');$('#sort-select').options[1].text=tr('sortRank');$('#sort-select').options[2].text=tr('sortWinrate');$('#search').placeholder=tr('search');
  $('#add-open').innerHTML='<span>＋</span> '+tr('addAccount');$('#empty-state h3').textContent=tr('emptyTitle');$('#empty-state p').textContent=tr('emptyText');$('#empty-add').innerHTML='<span>＋</span> '+tr('addFirst');$('footer span').textContent=tr('footer');
  $('#account-modal .modal-kicker').innerHTML='<span>◈</span> '+tr('newAccount');$('#account-modal .modal-description').textContent=tr('addDescription');
  $('label[for="riot-name"]').textContent='RIOT ID';$('#riot-name').placeholder=tr('summonerName');$('label[for="riot-username"]').textContent=tr('username');$('#riot-username').placeholder=tr('usernamePlaceholder');$('label[for="riot-password"]').textContent=tr('password');$('#riot-password').placeholder=tr('passwordPlaceholder');$('#account-modal .field-hint').textContent=tr('profileHint');$('label[for="account-label"]').innerHTML=tr('label')+' <span>'+tr('optional')+'</span>';$('#account-modal .modal-note span:last-child').textContent=tr('credentialNote');$('#submit-text').textContent=tr('addSubmit');
  $('#riot-id-modal .modal-kicker').innerHTML='<span>◈</span> '+tr('linkTitle');$('#riot-id-modal .modal-description').textContent=tr('linkDescription');$('label[for="edit-riot-name"]').textContent=tr('name');$('label[for="edit-riot-tag"]').textContent=tr('tag');$('#riot-id-submit-text').textContent=tr('linkSubmit');
  $('#settings-modal .modal-kicker').innerHTML='<span>◈</span> '+tr('preferences');$('.settings-title').textContent=tr('settings');$('#settings-modal .modal-description').textContent=tr('settingsDescription');$('#setting-close-after-login').closest('.setting-option').querySelector('b').textContent=tr('closeAfterLogin');$('#setting-close-after-login').closest('.setting-option').querySelector('small').textContent=tr('closeAfterLoginHelp');$('#setting-launch-windows').closest('.setting-option').querySelector('b').textContent=tr('launchWindows');$('#setting-launch-windows').closest('.setting-option').querySelector('small').textContent=tr('launchWindowsHelp');$('.setting-language>span').textContent=tr('language');$('#settings-save').textContent=tr('saveSettings');
  $('#setting-accounts-per-row-label').textContent=en?'Accounts per row':'Cuentas por fila';[...$('#setting-accounts-per-row').options].forEach(option=>option.textContent=en?option.value+' per row':option.value+' por fila');
  $('#login-modal .modal-kicker').innerHTML='<span>◈</span> '+tr('loginKicker');$('#login-description').textContent=tr('loginDescription');$('#login-step-client b').textContent=tr('stepClient');$('#login-step-client small').textContent=tr('stepClientHelp');$('#login-step-signout b').textContent=tr('stepSwitch');$('#login-step-signout small').textContent=tr('stepSwitchHelp');$('#login-step-credentials b').textContent=tr('stepCredentials');$('#login-step-credentials small').textContent=tr('stepCredentialsHelp');$('#login-step-verification b').textContent=tr('stepVerify');$('#login-step-verification small').textContent=tr('stepVerifyHelp');$('#login-step-league b').textContent=tr('stepLeague');$('#login-step-league small').textContent=tr('stepLeagueHelp');$('#login-close-app').textContent=tr('back');$('#login-update-progress [role="progressbar"]').setAttribute('aria-label',tr('progressLabel'));
  $('#update-title').textContent=en?'Preparing the new version':'Preparando la nueva versión';$('#update-message').textContent=en?'Checking for a newer version...':'Buscando una versión más reciente...';$('#update-apply').textContent=en?'RESTART':'REINICIAR';$('#update-close').textContent=en?'Continue with this version':'Continuar con esta versión';
  document.querySelectorAll('.modal-close').forEach(button=>button.setAttribute('aria-label',en?'Close':'Cerrar'));
  $('#settings-language').value=en?'en':'es';if(state.accounts.length)render();paintRefreshTimer();applyLoginStepLabels();$('#setting-launch-minimized-option .setting-copy b').textContent=tr('launchMinimized');$('#setting-launch-minimized-option .setting-copy small').textContent=tr('launchMinimizedHelp');
  const rankAscending=$('#sort-select').querySelector('[value="rank-asc"]');
  if(!rankAscending){const option=document.createElement('option');option.value='rank-asc';$('#sort-select').querySelector('[value="rank"]').after(option)}
  $('#sort-select').querySelector('[value="rank"]').textContent=tr('sortRank');
  $('#sort-select').querySelector('[value="rank-asc"]').textContent=tr('sortRankAsc');
  updatePlayWithButton();renderPlayWithOptions();
}
function tier(a){return a.tier&&tiers.includes(a.tier)?a.tier:'UNRANKED'}
function tierLabel(a){return tierName(tier(a))+(a.rank?' '+a.rank:'')}
function ti(a){return tiers.indexOf(tier(a))}
const divisions=['IV','III','II','I'];
function updatePlayWithButton(){const button=$('#play-with-open');if(!button)return;button.textContent=state.playWithTier?tr('playWith')+' '+tierName(state.playWithTier)+' · '+tr(state.playWithQueue==='flex'?'queueFlex':'queueSolo'):tr('playWith');button.setAttribute('aria-label',button.textContent)}
function renderPlayWithOptions(){
  const ranks=$('#play-with-ranks');if(!ranks)return;
  $('#play-with-title').textContent=tr('playWithTitle');
  document.querySelectorAll('[data-playwith-queue]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.playwithQueue===state.playWithQueue)));
  ranks.innerHTML=tiers.map(rank=>{const disabled=state.playWithQueue==='solo'&&['GRANDMASTER','CHALLENGER'].includes(rank);return '<button type="button" class="play-with-rank '+(state.playWithTier===rank?'selected':'')+'" data-playwith-tier="'+rank+'" aria-pressed="'+(state.playWithTier===rank)+'" '+(disabled?'disabled title="'+(state.settings.language==='en'?'Solo/Duo is unavailable for this rank':'No se puede jugar en Solo/Duo con este rango')+'"':'')+'><img src="/static/ranks/'+rank.toLowerCase()+'.png" alt=""><span>'+esc(tierName(rank))+'</span></button>'}).join('');
  $('#play-with-note').textContent=tr(state.playWithQueue==='flex'?'flexRulesNote':'soloRulesNote');
  $('#play-with-clear').textContent=tr('clearPlayWith');updatePlayWithButton();
}
function closePlayWithPopover(){const popover=$('#play-with-popover'),button=$('#play-with-open');if(popover){popover.hidden=true;button.setAttribute('aria-expanded','false')}}
function nextDivision(a){
  const currentTier=tier(a),tierIndex=tiers.indexOf(currentTier),rank=String(a.rank||'').toUpperCase(),divisionIndex=divisions.indexOf(rank);
  if(tierIndex<0||tierIndex>6||divisionIndex<0)return '';
  if(divisionIndex<divisions.length-1)return tierName(currentTier)+' '+divisions[divisionIndex+1];
  const nextTier=tiers[tierIndex+1];
  return nextTier==='MASTER'?tierName('MASTER'):nextTier?tierName(nextTier)+' IV':'';
}
function rankProgress(a){
  const target=nextDivision(a);
  if(!target)return '';
  const raw=Number(a.league_points)||0,lp=Math.max(0,Math.min(100,raw)),shown=Math.round(lp),remaining=Math.max(0,100-shown);
  const message=remaining===0?(state.settings.language==='en'?'PROMOTION READY':'PROMOCIÓN DISPONIBLE'):(state.settings.language==='en'?remaining+' LP TO '+target.toUpperCase():'FALTAN '+remaining+' LP PARA '+target.toUpperCase());
  return '<div class="rank-progress"><div class="rank-progress-label"><span>'+shown+' / 100 LP</span><small>'+esc(message)+'</small></div><div class="rank-progress-track" style="--lp-progress:'+lp+'%" role="progressbar" aria-label="Progreso hacia '+esc(target)+'" aria-valuemin="0" aria-valuemax="100" aria-valuenow="'+shown+'"></div></div>';
}
function renderFilters(){const n=Object.fromEntries([...tiers,'UNRANKED'].map(t=>[t,0]));state.accounts.forEach(a=>n[tier(a)]++);const rows=[['ALL',tr('all'),null],['UNRANKED',tierName('UNRANKED'),'unranked.png'],...tiers.map(t=>[t,tierName(t),t.toLowerCase()+'.png'])];$('#rank-filters').innerHTML=rows.map(r=>'<button class="rank-filter '+(state.tier===r[0]?'selected':'')+'" data-tier="'+r[0]+'" title="'+esc(r[1])+'" '+(r[0]==='ALL'?'aria-label="'+esc(tr('all'))+'"':'')+'>'+(r[2]?'<img src="/static/ranks/'+r[2]+'" alt="">':'<span class="'+(r[0]==='ALL'?'rank-filter-all':'rank-filter-unranked')+'">'+(r[0]==='ALL'?esc(tr('all')):'—')+'</span>')+(r[0]==='ALL'?'':'<span>'+esc(r[1])+'</span>')+'<b>'+(r[0]==='ALL'?state.accounts.length:n[r[0]])+'</b></button>').join('')}
function menuAction(attribute,id,key,icon){return '<button type="button" '+attribute+'="'+Number(id)+'"><span class="account-menu-icon" aria-hidden="true">'+icon+'</span><span>'+esc(tr(key).slice(2))+'</span></button>'}
function actionButton(className,attribute,value,label,icon){return '<button type="button" class="account-action '+className+'" '+attribute+'="'+esc(value)+'" aria-label="'+esc(tr(label))+'"><svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">'+icon+'</svg><span class="action-tooltip" role="tooltip">'+esc(tr(label))+'</span></button>'}
function card(a){
  const total=(a.wins||0)+(a.losses||0),wr=total?Math.round(a.wins*100/total):0,u=tier(a)==='UNRANKED';
  const name=String(a.game_name||'').trim(),tag=String(a.tag_line||'').trim(),hasId=Boolean(a.has_riot_id&&name&&tag);
  const profileIconId=Number(a.profile_icon_id),hasProfileIcon=a.profile_icon_id!==null&&a.profile_icon_id!==undefined&&Number.isSafeInteger(profileIconId)&&profileIconId>=0&&Boolean(a.icon_version),level=Number(a.summoner_level),levelBadge=Number.isSafeInteger(level)&&level>0?'<span class="profile-icon-level" aria-label="Nivel de cuenta '+level+'">'+level+'</span>':'',icon=hasProfileIcon?'<div class="profile-icon-wrap"><img class="profile-icon" src="https://ddragon.leagueoflegends.com/cdn/'+encodeURIComponent(a.icon_version)+'/img/profileicon/'+profileIconId+'.png" alt="Icono de perfil de '+esc(name)+'">'+levelBadge+'</div>':'';
  const identity='<div class="account-id-line"><span class="account-name">'+esc(name)+'</span>'+(hasId?'<span class="account-tag">#'+esc(tag)+'</span>':'')+'</div>'+(hasId?'':'<button class="link-riot-id" data-edit-riot="'+Number(a.id)+'">'+tr('link')+'</button>');
  const rankBlock=(rankTier,division,queueLabel)=>{const unranked=rankTier==='UNRANKED',rankSlug=unranked?'unranked':rankTier.toLowerCase(),label=tierName(rankTier)+(division&&!unranked?' '+division:'');return '<div class="queue-rank"><img class="rank-emblem-image" src="/static/ranks/'+rankSlug+'.png" alt="'+esc(tierName(rankTier))+'"><div class="rank-text"><b class="'+(unranked?'unranked':'')+'">'+esc(label)+'</b>'+(!unranked?'<small>'+queueLabel+'</small>':'')+'</div></div>'};
  const flexTier=tiers.includes(a.flex_tier)?a.flex_tier:'UNRANKED';
  const riotCopy=hasId?actionButton('copy-id','data-copy-riot-id',name+'#'+tag,'copy','<rect x="5" y="5" width="14" height="17" rx="2"/><path d="M9 5V3h6v2"/><path d="M8.5 10h7m-7 4h7m-7 4h4"/>'):'';
  const passwordCopy=actionButton('copy-password','data-copy-password',a.id,'copyPassword','<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/><circle cx="12" cy="15" r="1"/>');
  const signIn='<button class="login-btn" data-login="'+Number(a.id)+'">'+tr('login')+'</button>';
  return '<article class="account-card"><div class="card-top '+(hasProfileIcon?'has-profile-icon':'no-profile-icon')+'"><div class="account-identity">'+identity+'</div>'+icon+'<button class="card-menu" data-menu="'+Number(a.id)+'" aria-label="'+(state.settings.language==='en'?'Account options':'Opciones de cuenta')+'">⋯</button><div class="account-menu" id="menu-'+Number(a.id)+'" hidden>'+menuAction('data-refresh',a.id,'refresh','↻')+menuAction('data-edit-riot',a.id,'editRiot','◈')+menuAction('data-label',a.id,'editLabel','✎')+menuAction('data-delete',a.id,'deleteAccount','⌫')+'</div></div>'+(a.label?'<div class="account-label">'+esc(a.label)+'</div>':'')+'<div class="rank-row">'+rankBlock(tier(a),a.rank,tr('soloRanked'))+(flexTier!=='UNRANKED'?rankBlock(flexTier,a.flex_rank,tr('flexRanked')):'')+'</div>'+(!u&&hasId?rankProgress(a):'')+'<div class="card-footer"><span class="win-rate">'+(total?'<b>'+wr+'%</b> '+(state.settings.language==='en'?'WR · '+a.wins+'W / '+a.losses+'L':'WR · '+a.wins+'V / '+a.losses+'D'):tr('allGames'))+'</span><div class="card-actions">'+riotCopy+passwordCopy+signIn+'</div></div></article>'
}
function render(){
  const all=state.accounts;
  $('#heading-count').textContent='('+String(all.length).padStart(2,'0')+')';
  renderFilters();
  let list=all.filter(a=>(state.tier==='ALL'||tier(a)===state.tier)&&(!state.playWithTier||RankCompatibility.canPlayWith(a,state.playWithTier,state.playWithQueue))&&((a.game_name||'')+' '+(a.tag_line||'')+' '+(a.label||'')).toLowerCase().includes(state.query));
  if(state.sort==='rank'||state.sort==='rank-asc')list.sort((a,b)=>{
    const aTier=ti(a),bTier=ti(b);
    if(aTier<0||bTier<0)return aTier<0?(bTier<0?(a.game_name||'').localeCompare(b.game_name||''):1):-1;
    const direction=state.sort==='rank-asc'?1:-1;
    const aDivision=divisions.indexOf(String(a.rank||'').toUpperCase()),bDivision=divisions.indexOf(String(b.rank||'').toUpperCase());
    return direction*(aTier-bTier||((aDivision<0?0:divisions.length-aDivision)-(bDivision<0?0:divisions.length-bDivision))||((Number(a.league_points)||0)-(Number(b.league_points)||0)))||(a.game_name||'').localeCompare(b.game_name||'');
  });
  else if(state.sort==='winrate')list.sort((a,b)=>{const x=(a.wins||0)+(a.losses||0),y=(b.wins||0)+(b.losses||0);return(y?(b.wins||0)/y:0)-(x?(a.wins||0)/x:0)});
  else list.sort((a,b)=>(a.game_name||'').localeCompare(b.game_name||''));
  $('#accounts').innerHTML=list.map(card).join('');
  $('#accounts').style.setProperty('--account-columns',String(state.settings.accounts_per_row||3));
  $('#accounts').style.display=list.length?'grid':'none';
  $('#empty-state').classList.toggle('visible',all.length===0);
  let empty=$('#filter-empty');
  if(!empty){empty=document.createElement('div');empty.id='filter-empty';empty.className='empty-state';$('.collection').insertBefore(empty,$('footer'))}
  empty.innerHTML='<div class="empty-symbol">⌕</div><h3>'+tr('noFilterTitle')+'</h3><p>'+tr('noFilterText')+'</p><button class="clear-filters lol-button">'+tr('showAll')+'</button>';
  empty.classList.toggle('visible',all.length>0&&!list.length);
}
async function load(){try{state.accounts=await api('/api/accounts');render()}catch(e){toast(e.message)}}
function error(text,id='#form-error'){const el=$(id);el.textContent=localize(text);el.classList.add('visible')}
function clearError(id='#form-error'){const el=$(id);el.textContent='';el.classList.remove('visible')}
function setLoginStep(id,status){const el=$(id),current=['active','complete','failed'].find(name=>el.classList.contains(name));if(current===status)return;if(current)el.classList.remove(current);if(status)el.classList.add(status)}
function applyLoginStepLabels(){
  const en=state.settings.language==='en';
  const labels=en?[
    ['Open Riot Client','Start the Riot sign-in client'],
    ['Wait for Riot Client','Wait until its services are ready'],
    ['Close the current session','Sign out of the previous account if needed'],
    ['Connect to sign-in','Prepare Riot Client for authentication'],
    ['Find the sign-in screen','Open Riot’s native sign-in form'],
    ['Enter saved credentials','Fill in the securely stored credentials'],
    ['Verify the account','Complete any Riot security checks'],
    ['Launch League of Legends','Open the game with the selected account'],
  ]:[
    ['Abrir Riot Client','Iniciar el cliente de Riot'],
    ['Esperar a Riot Client','Esperar a que sus servicios estén listos'],
    ['Cerrar la sesión actual','Salir de la cuenta anterior si hace falta'],
    ['Conectar con el acceso','Preparar Riot Client para autenticarte'],
    ['Buscar la pantalla de acceso','Abrir el formulario nativo de Riot'],
    ['Introducir las credenciales','Rellenar los datos guardados de forma segura'],
    ['Verificar la cuenta','Completar las comprobaciones de seguridad de Riot'],
    ['Abrir League of Legends','Iniciar el juego con la cuenta elegida'],
  ];
  loginStepIds.forEach((id,index)=>{$(id+' b').textContent=labels[index][0];$(id+' small').textContent=labels[index][1]});
}
function loginMessage(message){
  if(state.settings.language!=='en')return message;
  const translations=[
    ['Riot está actualizando League of Legends','Riot is updating League of Legends'],
    ['Riot aceptó la sesión; esperando a que League of Legends se abra…','Riot accepted the sign-in; waiting for League of Legends to open…'],
    ['Riot confirmó la cuenta. Abriendo League of Legends…','Riot confirmed the account. Opening League of Legends…'],
    ['La cuenta ya está iniciada. Abriendo League of Legends…','This account is already signed in. Opening League of Legends…'],
    ['League of Legends está abierto con la cuenta seleccionada.','League of Legends is open with the selected account.'],
    ['El cliente de League of Legends está abierto con la cuenta seleccionada.','The League of Legends client is open with the selected account.'],
    ['Abriendo Riot Client…','Opening Riot Client…'],
    ['Preparando Riot Client…','Preparing Riot Client…'],
    ['Comprobando Riot Client…','Checking Riot Client…'],
    ['Esperando a que Riot Client esté listo…','Waiting for Riot Client to be ready…'],
    ['Esperando a que Riot Client prepare la sesión…','Waiting for Riot Client to prepare the session…'],
    ['Riot Client ya está listo.','Riot Client is ready.'],
    ['Comprobando la sesión actual…','Checking the current session…'],
    ['Cerrando la sesión anterior de Riot…','Signing out of the previous Riot account…'],
    ['Cerrando League of Legends antes de cambiar de cuenta…','Closing League of Legends before switching accounts…'],
    ['Conectando con el formulario de inicio de sesión…','Connecting to the sign-in form…'],
    ['Buscando la pantalla de inicio de sesión…','Looking for the sign-in screen…'],
    ['No hace falta abrir el formulario de inicio de sesión.','The sign-in form is not needed.'],
    ['La sesión de Riot ya está conectada.','Riot is already connected.'],
    ['No hace falta volver a introducir las credenciales.','There is no need to re-enter credentials.'],
    ['Riot ya confirmó esta cuenta.','Riot has already verified this account.'],
    ['Preparando el formulario seguro de Riot Client…','Preparing Riot Client’s secure sign-in form…'],
    ['Cargando el formulario nativo de Riot…','Loading Riot’s native sign-in form…'],
    ['Introduciendo las credenciales guardadas…','Entering the saved credentials…'],
    ['Esperando la confirmación de Riot…','Waiting for Riot to confirm…'],
    ['Riot requiere MFA o CAPTCHA. Complétalo en la ventana de Riot Client.','Riot requires MFA or CAPTCHA. Complete it in the Riot Client window.'],
  ];
  for(const [es,en] of translations)if(message.startsWith(es))return en+message.slice(es.length);
  return localize(message);
}
function paintLoginStatus(s){
  const step=s.step||'client',terminal=['success','error'].includes(s.state),stage={client:0,wait_client:1,signout:2,connect:3,find:4,credentials:5,typing:5,verification:6,launch:7,success:8},current=stage[step]??0;
  loginStepIds.forEach((selector,index)=>{const status=s.state==='success'||index<current?'complete':index===current&&!terminal?'active':'';setLoginStep(selector,status);$(selector+' .step-indicator').textContent=status==='complete'?'✓':String(index+1).padStart(2,'0')});
  if(s.state==='error'){const failedStep=loginStepIds[stage[step]??0];setLoginStep(failedStep,'failed');$(failedStep+' .step-indicator').textContent='!'}
  $('#login-description').textContent=s.state==='success'?'':s.state==='error'?(state.settings.language==='en'?'Sign-in could not be completed.':'No se pudo completar el inicio de sesión.'):tr('loginDescription');
  $('#login-success').hidden=s.state!=='success';
  if(s.state==='success'){
    const account=state.accounts.find(item=>item.id===Number(state.loginAccountId)),rankTier=account?tier(account):'UNRANKED',rankLabel=rankTier==='UNRANKED'?tr('rankUnranked'):tierName(rankTier)+(account?.rank?' '+account.rank:'');
    const emblem=$('#login-success-rank-icon');
    emblem.src='/static/ranks/'+(rankTier==='UNRANKED'?'unranked':rankTier.toLowerCase())+'.png';
    emblem.alt=rankLabel;
    $('#login-success-rank-label').textContent=rankLabel;
    $('#login-success-title').textContent=tr('loginSuccess');
    $('#login-success-account').textContent=account?(account.has_riot_id?account.game_name+'#'+account.tag_line:account.game_name):(state.settings.language==='en'?'Selected account':'Cuenta seleccionada');
  }
  const isUpdating=step==='launch'&&String(s.message||'').toLowerCase().includes('actualizando league of legends');
  $('#login-live-status').textContent=loginMessage(s.message||tr('process'));
  const progressBox=$('#login-update-progress'),progress=Number(s.progress),hasProgress=isUpdating&&s.progress!==null&&s.progress!==undefined&&Number.isFinite(progress);
  progressBox.hidden=!isUpdating;
  if(isUpdating){const value=hasProgress?Math.max(0,Math.min(100,progress)):0;$('#login-update-fill').style.width=value+'%';$('#login-update-percent').textContent=hasProgress?Math.round(value)+'%':'…';progressBox.querySelector('[role="progressbar"]').setAttribute('aria-valuenow',String(Math.round(value)));progressBox.classList.toggle('indeterminate',!hasProgress)}
  $('#login-close-app').hidden=s.state!=='success';
}
async function pollLoginStatus(id){
  try{
    const status=await api('/api/accounts/'+id+'/login-status');
    paintLoginStatus(status);
    if(status.state==='success'&&state.settings.close_after_login&&state.lastLoginCloseId!==Number(id)){state.lastLoginCloseId=Number(id);api('/api/app/close',{method:'POST'}).catch(e=>toast(e.message))}
    if(['starting','running','verification'].includes(status.state))setTimeout(()=>pollLoginStatus(id),500);
  }catch(e){paintLoginStatus({state:'error',step:'error',message:e.message})}
}
async function beginLogin(id){
  await loadSettings();
  state.lastLoginCloseId=null;
  state.loginAccountId=Number(id);
  const account=state.accounts.find(a=>a.id===Number(id));
  $('#login-account-name').textContent=(account?.game_name||(state.settings.language==='en'?'ACCOUNT':'CUENTA'))+(account?.has_riot_id?'#'+account.tag_line:'');
  $('#login-description').textContent=tr('loginDescription');
  $('#login-live-status').textContent=state.settings.language==='en'?'Opening Riot Client…':'Abriendo Riot Client…';
  $('#login-update-progress').hidden=true;$('#login-update-progress').classList.remove('indeterminate');
  $('#login-close-app').hidden=true;$('#login-success').hidden=true;
  for(const step of loginStepIds)setLoginStep(step,'');
  setLoginStep('#login-step-client','active');
  openModal('#login-modal','#login-backdrop');
  try{await api('/api/accounts/'+id+'/login',{method:'POST'});pollLoginStatus(id)}
  catch(e){paintLoginStatus({state:'error',step:'client',message:e.message})}
}
async function loadSettings(){try{state.settings=await api('/api/settings');applyLanguage()}catch(e){toast(e.message)}}
function updateLaunchMinimizedVisibility(){$('#setting-launch-minimized-option').hidden=!$('#setting-launch-windows').checked}
$('#setting-launch-windows').addEventListener('change',updateLaunchMinimizedVisibility);
function openSettings(){clearError('#settings-error');$('#setting-close-after-login').checked=state.settings.close_after_login;$('#setting-launch-windows').checked=state.settings.launch_on_windows;$('#setting-launch-minimized').checked=state.settings.launch_minimized;updateLaunchMinimizedVisibility();$('#settings-language').value=state.settings.language||'es';$('#setting-accounts-per-row').value=String(state.settings.accounts_per_row||3);openModal('#settings-modal','#settings-backdrop')}
async function saveSettings(){const button=$('#settings-save');button.disabled=true;clearError('#settings-error');try{state.settings=await api('/api/settings',{method:'PUT',body:JSON.stringify({close_after_login:$('#setting-close-after-login').checked,launch_on_windows:$('#setting-launch-windows').checked,launch_minimized:$('#setting-launch-minimized').checked,language:$('#settings-language').value,accounts_per_row:Number($('#setting-accounts-per-row').value)})});applyLanguage();closeModal($('#settings-backdrop'));toast(tr('settingsSaved'))}catch(e){error(e.message,'#settings-error')}finally{button.disabled=false}}
function paintRefreshTimer(){const label=$('#refresh-timer-label'),clock=$('#refresh-countdown');if(!label||!clock)return;if(state.refreshing){label.textContent=tr('refreshing');clock.textContent='···';return}label.textContent=tr('refreshTimer');const seconds=Math.max(0,state.refreshSeconds),minutes=String(Math.floor(seconds/60)).padStart(2,'0'),remaining=String(seconds%60).padStart(2,'0');clock.textContent=minutes+':'+remaining}
async function syncRefreshStatus(){try{const status=await api('/api/refresh/status');state.refreshing=Boolean(status.refreshing);if(!state.refreshing)state.refreshSeconds=Number(status.next_refresh_seconds)||0;if(status.last_refresh&&status.last_refresh!==state.lastRankRefresh){state.lastRankRefresh=status.last_refresh;await load()}paintRefreshTimer()}catch{}}
function editRiotId(id){const account=state.accounts.find(a=>a.id===Number(id));if(!account)return;state.editingAccountId=Number(id);$('#edit-riot-name').value=account.has_riot_id?account.game_name:'';$('#edit-riot-tag').value=account.has_riot_id?account.tag_line:'';clearError('#riot-id-error');$('#riot-id-submit-text').textContent=tr('linkSubmit');openModal('#riot-id-modal','#riot-id-backdrop')}
function cleanRiotIdText(value){return String(value??'').normalize('NFKC').replace(/[\u200B-\u200D\uFEFF\u2060]/g,'').replace(/\u00A0/g,' ').replace(/[\r\n\t]+/g,' ').replace(/\s+/g,' ').trim()}
function parsePastedRiotId(value){
  const cleaned=cleanRiotIdText(value).replace(/\s*#\s*/,'#');
  const separator=cleaned.indexOf('#');
  if(separator<=0||separator===cleaned.length-1)return null;
  const gameName=cleaned.slice(0,separator).trim(),tagLine=cleaned.slice(separator+1).trim();
  return gameName&&tagLine&&!tagLine.includes('#')?{gameName,tagLine}:null;
}
function handleRiotIdPaste(event){
  const parsed=parsePastedRiotId(event.clipboardData?.getData('text')||'');
  if(!parsed)return;
  event.preventDefault();
  const form=event.currentTarget.form;
  form.elements.game_name.value=parsed.gameName;
  form.elements.tag_line.value=parsed.tagLine;
  form.elements.tag_line.focus();
}
function normalizeRiotIdForm(form){
  const gameName=cleanRiotIdText(form.elements.game_name.value);
  const tagLine=cleanRiotIdText(form.elements.tag_line.value).replace(/^#/,'').trim();
  const parsed=parsePastedRiotId(gameName);
  if(parsed&&!tagLine)return parsed;
  return {gameName,tagLine};
}
async function writeClipboard(value){
  try{if(navigator.clipboard?.writeText){await navigator.clipboard.writeText(value);return}}
  catch{}
  const input=document.createElement('textarea');input.value=value;input.setAttribute('readonly','');input.style.position='fixed';input.style.opacity='0';document.body.appendChild(input);
  try{input.focus();input.select();if(!document.execCommand('copy'))throw Error('Clipboard write failed')}
  finally{input.remove()}
}
async function copyRiotId(value){try{await writeClipboard(value);toast(tr('copied')+value)}catch{toast(tr('copyFailed'))}}
async function copyAccountPassword(id){
  try{
    const result=await api('/api/accounts/'+id+'/password',{method:'POST'});
    try{await writeClipboard(result.password)}catch{toast(tr('passwordCopyFailed'));return}
    toast(tr('passwordCopied'));
  }catch(error){toast(error.message)}
}
document.addEventListener('click',async event=>{const button=event.target.closest('[data-copy-password]');if(button){event.preventDefault();await copyAccountPassword(button.dataset.copyPassword)}});
document.addEventListener('click',e=>{
  const target=e.target;
  if(!target.closest('.play-with-filter'))closePlayWithPopover();
  if(target.closest('#play-with-open')){const popover=$('#play-with-popover'),open=popover.hidden;popover.hidden=!open;$('#play-with-open').setAttribute('aria-expanded',String(open));if(open)renderPlayWithOptions();return}
  const queue=target.closest('[data-playwith-queue]');
  if(queue){state.playWithQueue=queue.dataset.playwithQueue;renderPlayWithOptions();render();return}
  const rank=target.closest('[data-playwith-tier]');
  if(rank&&!rank.disabled){state.playWithTier=state.playWithTier===rank.dataset.playwithTier?null:rank.dataset.playwithTier;renderPlayWithOptions();render();return}
  if(target.closest('#play-with-clear')){state.playWithTier=null;renderPlayWithOptions();render();return}
  if(target.closest('.clear-filters')){state.playWithTier=null;renderPlayWithOptions()}
});
document.addEventListener('keydown',e=>{if(e.key==='Escape')closePlayWithPopover()});
document.addEventListener('click',async e=>{const target=e.target,backdrop=target.closest('.modal-backdrop');if(target.closest('[data-close]')){closeModal(backdrop);return}const tierButton=target.closest('[data-tier]');if(tierButton){state.tier=tierButton.dataset.tier;render();return}if(target.closest('.clear-filters')){state.tier='ALL';state.query='';$('#search').value='';render();return}if(target.closest('#add-open,#empty-add')){clearError();$('#add-form').reset();openModal('#account-modal');return}if(target===$('#modal-backdrop')||target===$('#riot-id-backdrop')||target===$('#login-backdrop')){closeModal(target);return}if(target.closest('[data-menu]')){const id=target.closest('[data-menu]').dataset.menu;document.querySelectorAll('.account-menu').forEach(m=>m.hidden=true);$('#menu-'+id).hidden=false;return}if(target.closest('[data-edit-riot]')){editRiotId(target.closest('[data-edit-riot]').dataset.editRiot);return}if(target.closest('[data-copy-riot-id]')){const riotId=target.closest('[data-copy-riot-id]').dataset.copyRiotId;if(!riotId||!riotId.includes('#')){toast(tr('noRiotId'));return}await copyRiotId(riotId);return}if(target.closest('[data-login]')){await beginLogin(target.closest('[data-login]').dataset.login);return}if(target.closest('[data-delete]')){const id=target.closest('[data-delete]').dataset.delete;if(confirm(state.settings.language==='en'?'Delete this account from your collection?':'¿Eliminar esta cuenta de tu colección?'))try{await api('/api/accounts/'+id,{method:'DELETE'});await load();toast(state.settings.language==='en'?'Account deleted':'Cuenta eliminada')}catch(x){toast(x.message)}return}if(target.closest('[data-refresh]')){const id=target.closest('[data-refresh]').dataset.refresh;try{const a=await api('/api/accounts/'+id+'/refresh',{method:'POST'});state.accounts=state.accounts.map(x=>x.id===a.id?a:x);render();toast(tr('rankUpdated'))}catch(x){toast(x.message)}return}if(target.closest('[data-label]')){const id=target.closest('[data-label]').dataset.label,a=state.accounts.find(x=>x.id===Number(id)),label=prompt(tr('enterLabel'),a?.label||'');if(label!==null)try{const x=await api('/api/accounts/'+id,{method:'PATCH',body:JSON.stringify({label})});state.accounts=state.accounts.map(y=>y.id===x.id?x:y);render()}catch(x){toast(x.message)}return}if(!target.closest('.account-menu'))document.querySelectorAll('.account-menu').forEach(m=>m.hidden=true)});
document.querySelectorAll('#add-form, #riot-id-form').forEach(form=>form.elements.game_name.addEventListener('paste',handleRiotIdPaste));
$('#add-form').addEventListener('submit',async e=>{e.preventDefault();clearError();const form=e.currentTarget,data=Object.fromEntries(new FormData(form)),riotId=normalizeRiotIdForm(form);data.game_name=riotId.gameName;data.tag_line=riotId.tagLine;const button=form.querySelector('button[type=submit]'),text=$('#submit-text'),hasRiotId=Boolean(data.game_name||data.tag_line);button.disabled=true;text.textContent=hasRiotId?(state.settings.language==='en'?'LOOKING UP RIOT…':'CONSULTANDO RIOT…'):(state.settings.language==='en'?'ADDING ACCOUNT…':'AÑADIENDO CUENTA…');try{const account=await api('/api/accounts',{method:'POST',body:JSON.stringify(data)});state.accounts.push(account);render();closeModal($('#modal-backdrop'));form.reset();toast(account.game_name+tr('added'))}catch(x){error(x.message)}finally{button.disabled=false;text.textContent=tr('addSubmit')}});
$('#riot-id-form').addEventListener('submit',async e=>{e.preventDefault();clearError('#riot-id-error');const form=e.currentTarget,riotId=normalizeRiotIdForm(form),data={game_name:riotId.gameName,tag_line:riotId.tagLine},id=state.editingAccountId,button=form.querySelector('button[type=submit]'),text=$('#riot-id-submit-text');button.disabled=true;text.textContent=state.settings.language==='en'?'LOOKING UP RIOT…':'CONSULTANDO RIOT…';try{const account=await api('/api/accounts/'+id,{method:'PATCH',body:JSON.stringify(data)});state.accounts=state.accounts.map(a=>a.id===account.id?account:a);render();closeModal($('#riot-id-backdrop'));toast(tr('linked'))}catch(x){error(x.message,'#riot-id-error')}finally{button.disabled=false;text.textContent=tr('linkSubmit')}});
$('#search').addEventListener('input',e=>{state.query=e.target.value.trim().toLowerCase();render()});$('#sort-select').addEventListener('change',e=>{state.sort=e.target.value;render()});$('#login-close-app').addEventListener('click',()=>closeModal($('#login-backdrop')));$('#settings-open').addEventListener('click',openSettings);$('#settings-save').addEventListener('click',saveSettings);document.addEventListener('keydown',e=>{if(e.key==='Escape')document.querySelectorAll('.modal-backdrop.open').forEach(closeModal);if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();$('#search').focus()}});load();loadSettings();syncRefreshStatus();setInterval(()=>{if(!state.refreshing&&state.refreshSeconds>0)state.refreshSeconds--;paintRefreshTimer()},1000);setInterval(syncRefreshStatus,30000);
