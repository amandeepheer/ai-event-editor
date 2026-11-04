/* Pair only with the user's loopback companion. No external AI endpoints. */
class EngineClient {
  constructor({fetcher = (...args) => fetch(...args), delay = ms => new Promise(resolve => setTimeout(resolve,ms)), base = 'http://127.0.0.1:8765'} = {}) {
    if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(base)) throw new Error('Engine must use a loopback address');
    this.base=base; this.fetcher=fetcher; this.delay=delay; this.token='';
  }
  async request(path, body) {
    if (!this.token) throw new Error('Connect to your local engine first');
    if (!/^\/v1\/[a-z0-9/-]+$/.test(path)) throw new Error('Invalid engine endpoint');
    const controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
    let timer;
    try {
      const options={method:body===undefined?'GET':'POST',credentials:'omit',redirect:'error',
        headers:{Authorization:'Bearer '+this.token, ...(body===undefined?{}:{'Content-Type':'application/json'})}};
      if (controller) options.signal=controller.signal;
      if (body!==undefined) options.body=JSON.stringify(body);
      const call=(async()=>{
        const response=await this.fetcher(this.base+path,options);
        let result;
        try{result=await response.json();}
        catch(cause){const error=new Error('The local port returned an unexpected response. Check for another service using port 8765.');error.preventLaunch=true;throw error;}
        if (!response.ok) {const error=new Error(result.error || 'Local engine request failed ('+response.status+')');error.status=response.status;throw error;}
        return result;
      })();
      return await Promise.race([call,new Promise((_,reject)=>{
        timer=setTimeout(()=>{if(controller)controller.abort();reject(new Error('Local engine timed out. Check the helper is still running.'));},15000);
      })]);
    } finally { clearTimeout(timer); }
  }
  async connect(token) {
    this.token=token.trim();
    const health=await this.request('/v1/health');
    if(health.api_version!==1 || health.engine!=='AI Event Editor') {const error=new Error('Incompatible local engine. Update the plugin and helper together.');error.preventLaunch=true;throw error;}
    if(!health.ffmpeg || !health.ffprobe) {const error=new Error('Install FFmpeg and FFprobe on the helper PATH, then reconnect.');error.preventLaunch=true;throw error;}
    return health;
  }
  async operation(path,body,progress=()=>{}) {
    const submitted=await this.request(path,body);
    if(!/^[a-f0-9]{32}$/.test(submitted.job_id)) throw new Error('Invalid local engine job response');
    for (;;) {
      const job=await this.request('/v1/jobs/'+submitted.job_id);
      progress(job.progress || 'Working locally…');
      if(job.status==='completed')return job.result;
      if(job.status==='failed')throw new Error(job.error || 'Local processing failed');
      if(job.status!=='running')throw new Error('Unknown local engine job state');
      await this.delay(750);
    }
  }
}
module.exports={EngineClient};
