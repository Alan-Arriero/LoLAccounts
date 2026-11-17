(()=>{
  const $=id=>document.getElementById(id),overlay=$('update-overlay');
  let dismissed=false;
  const hide=()=>{dismissed=true;overlay.classList.remove('visible');overlay.setAttribute('aria-hidden','true')};
  $('update-close').addEventListener('click',hide);
  $('update-apply').addEventListener('click',async()=>{
    const button=$('update-apply');button.disabled=true;button.textContent='REINICIANDO...';
    try{await fetch('/api/update/apply',{method:'POST'})}
    catch{button.disabled=false;button.textContent='REINTENTAR'}
  });
  async function poll(){
    try{
      const r=await fetch('/api/update/status',{cache:'no-store'}),s=await r.json();
      if(['checking','downloading','ready','error'].includes(s.state)&&!dismissed){overlay.classList.add('visible');overlay.setAttribute('aria-hidden','false')}
      if(s.state==='checking'){
        $('update-title').textContent='Buscando nuevas versiones';
        $('update-message').textContent='Comprobando las releases públicas de GitHub...';
        $('update-progress').style.width='22%';$('update-percent').textContent='···';
      }else if(s.state==='downloading'){
        $('update-title').textContent='Descargando actualización';
        $('update-message').textContent='Rift Vault se actualizará al terminar la descarga.';
        const progress=Math.max(0,Math.min(99.9,Number(s.progress)||0));
        $('update-progress').style.width=progress.toFixed(2)+'%';
        $('update-percent').textContent=Math.floor(progress)+'%';
        $('update-version').textContent=s.latest_version||'';
      }else if(s.state==='ready'){
        $('update-title').textContent='Nueva versión lista';
        $('update-message').textContent='La descarga terminó. Reinicia para instalarla automáticamente.';
        $('update-progress').style.width='100%';$('update-percent').textContent='100%';
        $('update-version').textContent=s.latest_version||'';
        $('update-apply').hidden=false;
      }else if(s.state==='error'){
        $('update-title').textContent='No se pudo completar la actualización';
        $('update-message').textContent=s.error||'Comprueba tu conexión e inténtalo más tarde.';
        $('update-close').hidden=false;
      }
      if(s.state==='checking'||s.state==='downloading')setTimeout(poll,s.state==='downloading'?120:900);
    }catch{setTimeout(poll,2500)}
  }
  poll();
})();
