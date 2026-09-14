(() => {
  'use strict';
  const data = window.OMNI_DATA;
  if (!data) return;
  const $ = (s, root = document) => root.querySelector(s);
  const $$ = (s, root = document) => [...root.querySelectorAll(s)];
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const families = data.benchmarks.map(b => b.family);
  const firstOutput = b => Object.entries(b.outputs).find(([,value]) => value);
  const setMedia = (video, item) => {
    video.pause(); video.poster = item.poster; video.src = item.src; video.load();
  };
  const playSafely = video => video.play().catch(() => {});
  const dialog = $('#sample-dialog');
  const showDialog = html => {
    if (dialog.open) dialog.close();
    $('#dialog-content').innerHTML = html;
    dialog.showModal(); dialog.scrollTop = 0;
  };
  const stopDialogMedia = () => $$('video', dialog).forEach(v => v.pause());
  $('#dialog-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', stopDialogMedia);
  dialog.addEventListener('click', e => {
    if (e.target === dialog) {
      const r = dialog.getBoundingClientRect();
      if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) dialog.close();
    }
  });
  function openAsset(asset, title, description = '') {
    showDialog(`<div class="asset-viewer"><h2 id="dialog-title">${esc(title)}</h2>${asset.modality === 'video'
      ? `<video src="${esc(asset.src)}" poster="${esc(asset.poster)}" controls playsinline muted></video>`
      : `<img src="${esc(asset.src)}" alt="${esc(title)}">`}<p>${esc(description)}</p></div>`);
  }

  // Browse all available model outputs for the selected example.
  let benchIndex = 0, language = 'en';
  const bench = () => data.benchmarks[benchIndex];
  // Paper taxonomy: Table A.1 and the seven families in Table 3.
  // The 20 release folders are grouped under their corresponding paper family.
  const taxonomy=[
    {name:'Content',tasks:[['object','Object'],['character','Character'],['scene','Scene']]},
    {name:'Motion',tasks:[['action_reference','Action'],['camera_reference','Camera Motion']]},
    {name:'Style',tasks:[['style_reference','Style']]},
    {name:'Structure',tasks:[['greybox','Greybox'],['lineart','Line Art'],['rough_storyboard','Rough Storyboard']]},
    {name:'Narrative',tasks:[['multi_panel_storyboard','Multi-Panel Storyboard'],['story_ref','Story'],['continuation','Preceding-Shot']]},
    {name:'Multi-content',tasks:[['multi_content_reference','Multi-Content'],['multi_reference_composition','Compositional Grounding']]},
    {name:'Cross-aspect',tasks:[['mr2v_content_motion','Content + Motion'],['mr2v_content_presentation','Content + Style'],['multi_reference_lineart','Content + Line Art'],['multi_reference_storyboard','Content + Rough Storyboard'],['multi_panel_content_reference','Content + Multi-Panel Storyboard'],['multi_story_ref','Content + Story']]}
  ];
  let selectedFamily=0,selectedTask=0,visibleCases=[];
  const resultPosterObserver=new IntersectionObserver(entries=>entries.forEach(e=>{if(e.isIntersecting){e.target.poster=e.target.dataset.poster;resultPosterObserver.unobserve(e.target);}}),{rootMargin:'300px'});
  function updateCaseOptions(){
    const family=taxonomy[selectedFamily], task=family.tasks[selectedTask];
    $('#benchmark-families').innerHTML=taxonomy.map((f,i)=>`<button data-bench-family="${i}" aria-pressed="${i===selectedFamily}">${esc(f.name)}</button>`).join('');
    $('#benchmark-subtasks').hidden=family.tasks.length<2;
    $('#benchmark-subtasks').innerHTML=family.tasks.map(([key,label],i)=>`<button data-bench-task="${i}" aria-pressed="${i===selectedTask}">${esc(label)}</button>`).join('');
    $$('[data-bench-family]').forEach(button=>button.onclick=()=>{selectedFamily=Number(button.dataset.benchFamily);selectedTask=0;updateCaseOptions();});
    $$('[data-bench-task]').forEach(button=>button.onclick=()=>{selectedTask=Number(button.dataset.benchTask);updateCaseOptions();});
    visibleCases=data.benchmarks.map((b,i)=>i).filter(i=>data.benchmarks[i].task===task[0]);
    $('#benchmark-selection').textContent=`${family.name} / ${task[1]}`;
    $('#case-prev').disabled=$('#case-next').disabled=visibleCases.length<2;
    if(visibleCases.length)renderBenchmark(visibleCases[0]);
  }
  function moveCase(delta){if(!visibleCases.length)return;const position=visibleCases.indexOf(benchIndex);renderBenchmark(visibleCases[(position+delta+visibleCases.length)%visibleCases.length]);}
  $('#case-prev').onclick=()=>moveCase(-1);$('#case-next').onclick=()=>moveCase(1);
  function renderInstruction() {
    $('#bench-prompt').textContent = bench()['prompt_' + language];
    $$('.language-toggle [data-lang]').forEach(button => {
      const active = button.dataset.lang === language;
      button.classList.toggle('active', active); button.setAttribute('aria-pressed', active);
    });
  }
  function renderBenchmark(index) {
    benchIndex = index; const b = bench();
    $('#case-example-label').textContent=`Example ${visibleCases.indexOf(index)+1}`;
    $('#case-position').textContent=`${visibleCases.indexOf(index)+1} / ${visibleCases.length}`;
    $('#case-id').textContent = taxonomy[selectedFamily].tasks[selectedTask][1];
    $('#bench-references').innerHTML = b.references.map((r, i) => `<button class="bench-ref" data-reference="${i}" aria-label="Inspect ${esc(r.label)} reference ${i + 1}"><img src="${esc(r.poster)}" alt="${esc(r.label)} reference" loading="lazy">${r.modality === 'video' ? '<i>▶</i>' : ''}<span>${String(i + 1).padStart(2, '0')} / ${esc(r.label)}</span></button>`).join('');
    $$('[data-reference]').forEach(button => button.addEventListener('click', () => {
      const r = b.references[Number(button.dataset.reference)]; openAsset(r, r.label + ' reference', r.role_cn || '');
    }));
    const available = Object.keys(b.outputs).filter(k => b.outputs[k]);
    resultPosterObserver.disconnect();
    $$('#all-model-outputs video').forEach(v=>{v.pause();v.removeAttribute('src');v.load();});
    $('#all-model-outputs').innerHTML=Object.entries(data.models).map(([key,label])=>`<article class="all-model-card"><h4>${esc(label)}</h4>${b.outputs[key]?`<video src="${esc(b.outputs[key].src)}" data-poster="${esc(b.outputs[key].poster)}" muted playsinline controls preload="none" aria-label="${esc(label)} output for ${esc(b.id)}"></video><a href="${esc(b.outputs[key].src)}" target="_blank" rel="noopener" class="text-link">Open web video ↗</a>`:'<p class="unavailable-output">Output unavailable for this case.</p>'}</article>`).join('');
    $$('#all-model-outputs video').forEach(v=>resultPosterObserver.observe(v));
    $('#all-models-count').textContent=`${available.length} / ${Object.keys(data.models).length} model outputs available · ${taxonomy[selectedFamily].tasks[selectedTask][1]} · Example ${visibleCases.indexOf(index)+1}`;
    $$('#all-model-outputs video').forEach(v=>v.addEventListener('error',()=>{v.insertAdjacentHTML('afterend','<p class="evidence-note">Browser playback unavailable. Use the original video link.</p>');},{once:true}));
    $('#bench-prompt').classList.remove('expanded'); $('#expand-prompt').setAttribute('aria-expanded', 'false'); $('#expand-prompt').textContent = 'Read full instruction +';
    renderInstruction();
  }
  $$('[data-lang]').forEach(button => button.addEventListener('click', () => { language = button.dataset.lang; renderInstruction(); }));
  $('#expand-prompt').addEventListener('click', () => {
    const expanded = $('#bench-prompt').classList.toggle('expanded');
    $('#expand-prompt').textContent = expanded ? 'Collapse instruction −' : 'Read full instruction +';
    $('#expand-prompt').setAttribute('aria-expanded', expanded);
  });

  updateCaseOptions();


  $('.menu-toggle').addEventListener('click', () => {
    const open = $('.site-header nav').classList.toggle('open');
    $('.menu-toggle').setAttribute('aria-expanded', open);
  });
  $$('.site-header nav a').forEach(a => a.addEventListener('click', () => {
    $('.site-header nav').classList.remove('open'); $('.menu-toggle').setAttribute('aria-expanded', false);
  }));
  if ('IntersectionObserver' in window) {
    document.documentElement.classList.add('js-on');
    const observer = new IntersectionObserver(entries => entries.forEach(e => {
      if(e.isIntersecting) { e.target.classList.add('visible'); observer.unobserve(e.target); }
    }), {threshold:.04});
    $$('.reveal').forEach(e => observer.observe(e));
  }

  document.addEventListener('visibilitychange',()=>{if(document.hidden){stopDialogMedia();$$('#all-model-outputs video').forEach(v=>v.pause());}});
})();
