const API_BASE = window.AHMED_AI_OS_API || "http://localhost:8000";
async function load(){
  const health=document.getElementById("health");
  try { const h=await fetch(API_BASE+"/health"); if(!h.ok) throw new Error(); health.textContent="API online"; }
  catch { health.textContent="API offline"; return; }
  try { const r=await fetch(API_BASE+"/v1/business/snapshot"); const s=await r.json();
    document.getElementById("revenue").textContent=String(s.won_revenue ?? "—");
    document.getElementById("leads").textContent=String(s.leads ?? "—");
    document.getElementById("qualified").textContent=String(s.qualified_leads ?? "—");
    document.getElementById("campaigns").textContent=String(s.active_campaigns ?? "—");
  } catch { /* dashboard remains usable when optional business data is unavailable */ }
}
load();
