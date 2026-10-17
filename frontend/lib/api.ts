const API=process.env.NEXT_PUBLIC_API_URL||'http://localhost:8000';
export async function api(path:string,opts:RequestInit={}){const token=typeof window!=='undefined'?localStorage.getItem('token'):null;const res=await fetch(API+path,{...opts,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{}) ,...(opts.headers||{})},cache:'no-store'});if(!res.ok) throw new Error((await res.json().catch(()=>({detail:'Request failed'}))).detail||'Request failed');return res.json()}

export async function downloadFile(path: string, defaultFilename: string = 'cloudsense_costs.csv') {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  const res = await fetch(API + path, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error('Download failed');
  const blob = await res.blob();
  const disposition = res.headers.get('Content-Disposition');
  let filename = defaultFilename;
  if (disposition && disposition.includes('filename=')) {
    filename = disposition.split('filename=')[1].replace(/['"]/g, '').trim();
  }
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}
