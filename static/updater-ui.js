(()=>{
  const $=id=>document.getElementById(id),overlay=$('update-overlay');
  const text=(es,en)=>{try{return localStorage.getItem('rift-vault-language')==='en'?en:es}catch{return es}};
  let dismissed=false;
  const hide=()=>{dismissed=true;overlay.classList.remove('visible');overlay.setAttribute('aria-hidden','true')};
  $('update-close').addEventListener('click',hide);
  $('update-apply').addEventListener('click',async()=>{
    const button=$('update-apply');button.disabled=true;button.textContent=text('REINICIANDO...','RESTARTING...');
    try{await fetch('/api/update/apply',{method:'POST'})}
    catch{button.disabled=false;button.textContent=text('REINTENTAR','TRY AGAIN')}
  });
  async function poll(){
    try{
      const r=await fetch('/api/update/status',{cache:'no-store'}),s=await r.json();
      if(['checking','downloading','ready','error'].includes(s.state)&&!dismissed){overlay.classList.add('visible');overlay.setAttribute('aria-hidden','false')}
      if(s.state==='checking'){
        $('update-title').textContent=text('Buscando nuevas versiones','Checking for updates');
        $('update-message').textContent=text('Comprobando las releases públicas de GitHub...','Checking public GitHub releases...');
        $('update-progress').style.setProperty('--progress','22%');$('update-percent').textContent='···';
      }else if(s.state==='downloading'){
        $('update-title').textContent=text('Descargando actualización','Downloading update');
        $('update-message').textContent=text('Rift Vault se actualizará al terminar la descarga.','Rift Vault will update when the download finishes.');
        const progress=Math.max(0,Math.min(99.9,Number(s.progress)||0));
        $('update-progress').style.setProperty('--progress',progress.toFixed(2)+'%');
        $('update-percent').textContent=Math.floor(progress)+'%';
        $('update-version').textContent=s.latest_version||'';
      }else if(s.state==='ready'){
        $('update-title').textContent=text('Nueva versión lista','New version ready');
        $('update-message').textContent=text('La descarga terminó. Reinicia para instalarla automáticamente.','The download is complete. Restart to install it automatically.');
        $('update-progress').style.setProperty('--progress','100%');$('update-percent').textContent='100%';
        $('update-version').textContent=s.latest_version||'';
        $('update-apply').hidden=false;
      }else if(s.state==='error'){
        $('update-title').textContent=text('No se pudo completar la actualización','Update could not be completed');
        $('update-message').textContent=s.error||(text('Comprueba tu conexión e inténtalo más tarde.','Check your connection and try again later.'));
        $('update-close').hidden=false;
      }else if(s.state==='current'){
        overlay.classList.remove('visible');overlay.setAttribute('aria-hidden','true');
      }
      if(s.state==='checking'||s.state==='downloading')setTimeout(poll,s.state==='downloading'?120:900);
    }catch{setTimeout(poll,2500)}
  }
  poll();
})();
