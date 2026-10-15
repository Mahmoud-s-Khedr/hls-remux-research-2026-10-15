const {chromium} = require('/home/mk/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs = require('fs');
const path = require('path');
const root = path.resolve(__dirname, '../outputs/hls-benchmark');

(async()=>{
  const browser = await chromium.launch({headless:true, executablePath:'/home/mk/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome', args:['--autoplay-policy=no-user-gesture-required']});
  const page = await browser.newPage();
  await page.goto('http://127.0.0.1:8765/work/player-test.html');
  const results = JSON.parse(fs.readFileSync(path.join(root,'results.json')));
  const priorPath=path.join(root,'browser-validation.json');
  const checks = fs.existsSync(priorPath) ? JSON.parse(fs.readFileSync(priorPath)) : {browser:await browser.version(), player:'hls.js 1.6.13', playbackRate:8, tests:[]};
  for(const fixture of results.fixtures) for(const [kind,data] of Object.entries(fixture.outputs)) {
    if(process.env.SKIP_KEYS?.split(',').includes(fixture.key))continue;
    if(process.env.ONLY_KEYS && !process.env.ONLY_KEYS.split(',').includes(fixture.key))continue;
    if(!data.warmup_ok) continue;
    const url = '/outputs/hls-benchmark/'+data.playlist;
    const test = await page.evaluate(async (url)=>{
      const video = document.querySelector('video');
      const errors=[];
      let hls;
      let result;
      const events=[];
      try {
        result = await new Promise((resolve,reject)=>{
          const timer=setTimeout(()=>reject(new Error('Playback timed out')),30000);
          video.onended=()=>{clearTimeout(timer);resolve({ended:true,currentTime:video.currentTime,duration:video.duration,
            width:video.videoWidth,height:video.videoHeight,quality:video.getVideoPlaybackQuality(),events});};
          video.onerror=()=>{clearTimeout(timer);reject(new Error('Media error '+video.error?.code+': '+video.error?.message));};
          hls=new Hls({debug:false});
          hls.on(Hls.Events.ERROR,(_,data)=>{
            errors.push({type:data.type,details:data.details,fatal:data.fatal});
            if(data.fatal){clearTimeout(timer);reject(new Error('Fatal HLS error '+data.details));}
          });
          let started=false;
          hls.on(Hls.Events.MANIFEST_PARSED,async()=>{
            if(started)return; started=true;
            try {
              video.muted=true; video.playbackRate=8;
              await video.play(); events.push('playing');
              // Exercise seeking, then play the complete asset from its beginning.
              await new Promise((res,rej)=>{
                const seekTimer=setTimeout(()=>rej(new Error('Seek timed out')),8000);
                video.addEventListener('seeked',()=>{clearTimeout(seekTimer);res();},{once:true});
                video.currentTime=18;
              });
              events.push('seeked-to-18s');
              await new Promise((res,rej)=>{
                const seekTimer=setTimeout(()=>rej(new Error('Seek back timed out')),8000);
                video.addEventListener('seeked',()=>{clearTimeout(seekTimer);res();},{once:true});
                video.currentTime=0;
              });
              events.push('seeked-to-start');
              await video.play();
            }catch(e){clearTimeout(timer);reject(e);}
          });
          hls.loadSource(url); hls.attachMedia(video);
        });
        result.passed=result.ended && result.width===1920 && result.height===1080 && !errors.length;
      }catch(e){result={passed:false,error:String(e)};}
      finally {if(hls)hls.destroy();video.pause();video.removeAttribute('src');video.load();}
      return {...result,errors};
    },url);
    checks.tests=checks.tests.filter(t=>!(t.container===fixture.key && t.kind===kind));
    checks.tests.push({container:fixture.key,kind,playlist:data.playlist,...test});
    fs.writeFileSync(path.join(root,'browser-validation.json'),JSON.stringify(checks,null,2));
    console.log(fixture.key,kind,test.passed,test.error||'',test.errors);
  }
  await browser.close();
})().catch(e=>{console.error(e);process.exitCode=1;});
