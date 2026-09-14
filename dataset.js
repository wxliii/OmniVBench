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
  const fmtTime = value => {
    const total = Math.max(0, Math.floor(value || 0));
    return `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`;
  };
  // Play a reference video and the target together, scrubbing by the same fraction.
  function createSyncBar(selector, collect) {
    const bar = $(selector);
    const nothing = { stop() {}, refresh() {}, show() {} };
    if (!bar) return nothing;
    const button = $('.transport-play', bar), seek = $('input[type=range]', bar);
    const time = $('.mono', bar), reset = $('.subtle-button', bar);
    let playing = false, frame = 0;
    const stop = () => {
      playing = false; cancelAnimationFrame(frame);
      button.innerHTML = '▶ <span>Play together</span>';
      button.setAttribute('aria-label', 'Play reference and target together');
      collect().forEach(v => v.pause());
    };
    // Wait until every clip can actually play: starting straight away makes them drift apart.
    const ready = video => new Promise(resolve => {
      if (video.readyState >= 2) return resolve();
      video.addEventListener('loadeddata', resolve, { once: true });
      video.addEventListener('error', resolve, { once: true });
    });
    const align = () => {
      const [lead, ...rest] = collect();
      if (!lead || !Number.isFinite(lead.duration) || !lead.duration) return;
      const fraction = lead.currentTime / lead.duration;
      rest.forEach(v => {
        if (!Number.isFinite(v.duration)) return;
        const wanted = fraction * v.duration;
        if (Math.abs(v.currentTime - wanted) > 0.1) v.currentTime = wanted;
      });
      seek.value = Math.round(fraction * 1000);
      time.textContent = fmtTime(lead.currentTime);
    };
    const tick = () => {
      if (!playing) return;
      align();
      frame = requestAnimationFrame(tick);
    };
    button.addEventListener('click', async () => {
      if (playing) return stop();
      const videos = collect();
      if (videos.length < 2) return;
      stopEverything();
      videos.forEach(v => { if (!v.src) v.src = v.dataset.src; });
      playing = true;
      button.innerHTML = 'Ⅱ <span>Pause together</span>';
      button.setAttribute('aria-label', 'Pause reference and target');
      await Promise.all(videos.map(ready));
      if (!playing) return;
      videos.forEach(v => { v.currentTime = 0; });
      try {
        await Promise.all(videos.map(v => v.play()));
      } catch (error) {
        stop();
        return;
      }
      frame = requestAnimationFrame(tick);
    });
    reset.addEventListener('click', () => {
      stop();
      collect().forEach(v => { if (v.readyState) v.currentTime = 0; });
      seek.value = 0; time.textContent = '00:00';
    });
    seek.addEventListener('input', () => {
      const fraction = Number(seek.value) / 1000;
      collect().forEach(v => { if (Number.isFinite(v.duration)) v.currentTime = fraction * v.duration; });
    });
    return {
      stop,
      refresh() {
        stop();
        collect().forEach(v => v.addEventListener('ended', stop));
        seek.value = 0; time.textContent = '00:00';
      },
      show(flag) { bar.hidden = !flag; },
    };
  }
  const singleSync = createSyncBar('#single-transport',
    () => [...$$('#single-media video'), $('#single-target')].filter(Boolean));
  const compositionSync = createSyncBar('#composition-transport',
    () => [...$$('#composition-refs video'), $('#composition-target')].filter(Boolean));
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

  let sampleLanguage = 'en';
  function openSample(sample) {
    showDialog(`<div class="dialog-heading"><span class="eyebrow">OMNI-R2V DATASET / ${esc(sample.family).toUpperCase()}</span><h2 id="dialog-title">${esc(sample.title)}</h2><p>${esc(sample.id)}</p></div><div class="dialog-view"><div class="dialog-refs">${sample.references.map((r, i) => `<div>${r.modality === 'video' ? `<video src="${esc(r.src)}" poster="${esc(r.poster)}" muted playsinline controls preload="none" aria-label="${esc(r.label)} reference"></video>` : `<img src="${esc(r.src)}" alt="${esc(r.label)} reference ${i + 1}">`}<span>${String(i + 1).padStart(2, '0')} / INPUT ${r.group || '—'} · ${esc(r.label).replaceAll('_',' ').toUpperCase()}</span></div>`).join('')}</div><div class="dialog-target"><span class="mono">THE TRAINING TARGET</span><video src="${esc(sample.target.src)}" poster="${esc(sample.target.poster)}" muted playsinline controls preload="metadata" aria-label="Training target video"></video></div></div><div class="dialog-prompt"><div class="prompt-header"><span class="eyebrow">ORIGINAL INSTRUCTION</span><div class="language-toggle"><button data-sample-lang="en">EN</button><button data-sample-lang="cn">中文</button></div></div><p id="sample-prompt"></p></div>`);
    const setLanguage = lang => {
      sampleLanguage = lang; $('#sample-prompt').textContent = sample['prompt_' + lang];
      $$('[data-sample-lang]').forEach(b => { b.classList.toggle('active', b.dataset.sampleLang === lang); b.setAttribute('aria-pressed', b.dataset.sampleLang === lang); });
    };
    $$('[data-sample-lang]').forEach(b => b.addEventListener('click', () => setLanguage(b.dataset.sampleLang)));
    setLanguage(sampleLanguage);
  }
  const wall = $('#dataset-wall');
  const roleLabel = r => r.label.replaceAll('_',' ');
  const coverRefs = d => {
    const selected=[], groups=new Set(), roles=new Set();
    d.references.forEach(ref=>{if(!roles.has(ref.label)){roles.add(ref.label);groups.add(ref.group||ref.label);selected.push(ref);}});
    d.references.forEach(ref=>{const key=ref.group||ref.label;if(selected.length<4&&!groups.has(key)){groups.add(key);selected.push(ref);}});
    d.references.forEach(ref=>{if(selected.length<4&&!selected.includes(ref))selected.push(ref);});
    return selected.slice(0,4);
  };
  const columns=Array.from({length:5},()=>[]);
  data.datasets.forEach((d,i)=>columns[i%5].push(d));
  wall.innerHTML=columns.map((items,c)=>`<div class="wall-column" style="--column:${c}">${items.map(d=>`<button class="wall-tile" data-wall-sample="${esc(d.id)}" aria-label="Inspect ${esc(d.title)} with ${d.references.length} references"><video src="${esc(d.target.src)}" poster="${esc(d.target.poster)}" muted loop playsinline preload="none" data-wall-video aria-hidden="true" tabindex="-1"></video><div class="wall-tile-caption"><span>${esc(d.family)}</span><span>${d.references.length} REFS → TARGET</span></div><div class="wall-ref-set">${coverRefs(d).map((ref,i)=>`<div class="wall-ref"><img src="${esc(ref.poster)}" alt=""><span>${esc(roleLabel(ref))}</span></div>`).join('')}${d.references.length>4?`<span class="wall-ref-extra">+${d.references.length-4}</span>`:''}</div></button>`).join('')}</div>`).join('');
  $$('[data-wall-sample]').forEach(button=>button.addEventListener('click',()=>openSample(data.datasets.find(d=>d.id===button.dataset.wallSample))));

  const singleTasks=[['action','Motion · Action'],['camera_motion','Motion · Camera'],['content','Content'],['style','Style'],['lineart','Structure · Line art'],['greybox','Structure · Greybox'],['rough_storyboard','Structure · Rough storyboard'],['preceding_shot','Narrative · Preceding shot'],['multi_panel_storyboard','Narrative · Multi-panel storyboard']];
  const inputGroups=d=>new Set(d.references.map(r=>r.group||1)).size;
  const singleExamples=singleTasks.map(([task,label])=>({label,samples:data.datasets.filter(d=>d.subtask===task && inputGroups(d)===1)})).filter(d=>d.samples.length);
  let singleTask=0, singlePosition=0, singleLanguage='en';
  function singlePrompt(){
    $('#single-instruction').textContent=singleExamples[singleTask].samples[singlePosition]['prompt_'+singleLanguage];
    $$('[data-single-lang]').forEach(b=>{const active=b.dataset.singleLang===singleLanguage;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));});
  }
  const singleFamilies=['Motion','Content','Style','Structure','Narrative'];
  function renderSingleTabs(){
    const family=singleExamples[singleTask].samples[0].family;
    $('#single-families').innerHTML=singleFamilies.map(f=>`<button data-single-family="${f}" aria-pressed="${f===family}">${f}</button>`).join('');
    const children=singleExamples.map((item,index)=>({item,index})).filter(({item})=>item.samples[0].family===family);
    $('#single-tabs').hidden=children.length<2;
    $('#single-tabs').innerHTML=children.map(({item,index})=>`<button data-single="${index}" aria-pressed="${index===singleTask}">${esc(item.label.split(' · ').pop())}</button>`).join('');
    $$('[data-single-family]').forEach(b=>b.onclick=()=>renderSingle(singleExamples.findIndex(item=>item.samples[0].family===b.dataset.singleFamily)));
    $$('[data-single]').forEach(b=>b.onclick=()=>renderSingle(Number(b.dataset.single)));
  }
  function stopSingleMedia(){
    singleSync.stop();
    $('#single-target').pause();
    $$('#single-media video').forEach(v=>v.pause());
  }
  function renderSingle(index,position=0){
    singleTask=index;singlePosition=position;
    stopSingleMedia();
    const items=singleExamples[index].samples;
    const d=items[position], ref=d.references[0];
    $('#single-position').textContent=`${position+1} / ${items.length}`;
    $('#single-prev').disabled=$('#single-next').disabled=items.length<2;
    $('#single-role').textContent=`${ref.modality.toUpperCase()} REFERENCE / ${roleLabel(ref)}`;
    // One input group can hold several assets of the same reference.
    $('#single-media').innerHTML=d.references.map(r=>r.modality==='video'
      ? `<video src="${esc(r.src)}" poster="${esc(r.poster)}" controls muted playsinline preload="none" aria-label="${esc(roleLabel(r))} input reference"></video>`
      : `<img src="${esc(r.src)}" alt="${esc(roleLabel(r))} input reference" loading="lazy">`).join('');
    setMedia($('#single-target'),d.target);
    const refVideos=$$('#single-media video');
    refVideos.forEach(v=>v.muted=true);
    singleSync.show(refVideos.length>0);
    singleSync.refresh();
    $('#single-caption').textContent=`${d.references.length} reference asset${d.references.length>1?'s':''} · 1 input group · ${d.id}`;
    singlePrompt();
    $('#single-open').onclick=()=>openSample(d);
    renderSingleTabs();
  }
  $('#single-prev').onclick=()=>renderSingle(singleTask,(singlePosition-1+singleExamples[singleTask].samples.length)%singleExamples[singleTask].samples.length);
  $('#single-next').onclick=()=>renderSingle(singleTask,(singlePosition+1)%singleExamples[singleTask].samples.length);
  $$('[data-single-lang]').forEach(b=>b.onclick=()=>{singleLanguage=b.dataset.singleLang;singlePrompt();});
  if(singleExamples.length)renderSingle(0);
  new IntersectionObserver(entries=>{if(!entries[0].isIntersecting)stopSingleMedia();}).observe($('.single-reference-section'));
  document.addEventListener('visibilitychange',()=>{if(document.hidden)stopSingleMedia();});

  // Reference groups come directly from inputs[]; semantic subject indices are not inferred.
  const compositionTasks=['multi_content','content_style','content_lineart','content_storyboard'];
  const examples=compositionTasks.map(task=>data.datasets.filter(d=>d.subtask===task)).filter(items=>items.length);
  let compositionTask=0,compositionPosition=0,compositionLanguage='en';
  function compositionPrompt(){
    $('#composition-instruction').textContent=examples[compositionTask][compositionPosition]['prompt_'+compositionLanguage];
    $$('[data-composition-lang]').forEach(b=>{const active=b.dataset.compositionLang===compositionLanguage;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));});
  }
  function renderCompositionTabs(){
    const family=examples[compositionTask][0].family;
    $('#composition-families').innerHTML=['Multi-content','Cross-aspect'].map(f=>`<button data-composition-family="${f}" aria-pressed="${f===family}">${f}</button>`).join('');
    const children=examples.map((items,index)=>({items,index})).filter(({items})=>items[0].family===family);
    $('#composition-tabs').hidden=children.length<2;
    $('#composition-tabs').innerHTML=children.map(({items,index})=>`<button data-composition="${index}" aria-pressed="${index===compositionTask}">${esc(items[0].title)}</button>`).join('');
    $$('[data-composition-family]').forEach(b=>b.onclick=()=>renderComposition(examples.findIndex(items=>items[0].family===b.dataset.compositionFamily)));
    $$('[data-composition]').forEach(b=>b.onclick=()=>renderComposition(Number(b.dataset.composition)));
  }
  function renderComposition(index,position=0){
    compositionTask=index;compositionPosition=position;
    const items=examples[index], d=items[position];
    $('#composition-position').textContent=`${position+1} / ${items.length}`;
    $('#composition-prev').disabled=$('#composition-next').disabled=items.length<2;
    const groups=new Map();
    d.references.forEach(ref=>{const key=ref.group||ref.label;if(!groups.has(key))groups.set(key,[]);groups.get(key).push(ref);});
    $('#composition-refs').innerHTML=[...groups.entries()].map(([key,refs],i)=>`<div class="composition-group"><span class="eyebrow">INPUT ${i+1} / ${esc(roleLabel(refs[0]))}</span><div class="composition-assets">${refs.map(ref=>ref.modality==='video'
      ? `<figure><video src="${esc(ref.src)}" poster="${esc(ref.poster)}" muted playsinline controls preload="none" aria-label="${esc(roleLabel(ref))} video reference"></video><figcaption>VIDEO REFERENCE</figcaption></figure>`
      : `<figure><img src="${esc(ref.poster)}" alt="${esc(roleLabel(ref))} reference" loading="lazy"><figcaption>IMAGE REFERENCE</figcaption></figure>`).join('')}</div></div>`).join('');
    setMedia($('#composition-target'),d.target);
    compositionSync.show($$('#composition-refs video').length>0);
    compositionSync.refresh();
    $('#composition-caption').textContent=`${d.references.length} reference assets · ${groups.size} input groups · ${d.id}`;
    compositionPrompt();
    $('#composition-open').onclick=()=>openSample(d);
    renderCompositionTabs();
  }
  $('#composition-prev').onclick=()=>renderComposition(compositionTask,(compositionPosition-1+examples[compositionTask].length)%examples[compositionTask].length);
  $('#composition-next').onclick=()=>renderComposition(compositionTask,(compositionPosition+1)%examples[compositionTask].length);
  $$('[data-composition-lang]').forEach(b=>b.onclick=()=>{compositionLanguage=b.dataset.compositionLang;compositionPrompt();});
  if(examples.length)renderComposition(0);
  new IntersectionObserver(entries=>{if(!entries[0].isIntersecting)$('#composition-target').pause();}).observe($('#composition-target'));
  let motion = !reduceMotion, coverVisible = true;
  const videos = $$('[data-wall-video]');
  // Play only six previews at once; all other tiles retain their real target posters.
  const active = videos.filter((v,i)=>[1,3,7,8,10,12].includes(i));
  function updateMotion(){
    const running = motion && coverVisible && !document.hidden;
    document.body.classList.toggle('wall-paused', !running);
    videos.forEach(v=>{if(running && active.includes(v)) playSafely(v);else v.pause();});
    $('#wall-motion').textContent=motion?'Pause motion Ⅱ':'Play motion ▶';
    $('#wall-motion').setAttribute('aria-pressed',String(motion));
  }
  $('#wall-motion').addEventListener('click',()=>{motion=!motion;updateMotion();});
  new IntersectionObserver(entries=>{coverVisible=entries[0].isIntersecting;updateMotion();},{threshold:.05}).observe($('.immersive-cover'));
  let scheduled=false;
  function scrollFrame(){
    const progress=Math.min(1,window.scrollY/innerHeight);
    document.body.style.setProperty('--cover-progress',progress);
    scheduled=false;
  }
  addEventListener('scroll',()=>{if(!reduceMotion&&!scheduled){scheduled=true;requestAnimationFrame(scrollFrame);}},{passive:true});
  if(!reduceMotion && matchMedia('(pointer:fine)').matches){
    $('.immersive-cover').addEventListener('pointermove',e=>{
      wall.style.setProperty('--pointer-x',`${(e.clientX/innerWidth-.5)*18}px`);
      wall.style.setProperty('--pointer-y',`${(e.clientY/innerHeight-.5)*12}px`);
    });
  }
  document.addEventListener('visibilitychange',()=>{updateMotion();if(document.hidden) {stopDialogMedia();$('#composition-target').pause();}});
  updateMotion();

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

})();
