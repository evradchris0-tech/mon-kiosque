"""Gabarits HTML de la console : légers (pas de framework), lisibles sur téléphone, clair/sombre."""

from __future__ import annotations

from html import escape

CSS = """
:root{--bg:#f7f7f7;--carte:#fff;--texte:#1a1a1a;--doux:#6b6b6b;--bord:#ededed;--orange:#ff7900;--orange-fonce:#e65100;--violet:#6a5acd;
--vert:#2e7d32;--rouge:#d32f2f;--ambre:#f9a825;--bulle-moi:#dcf8c6;--bulle-moki:#fff;--fond-chat:#ece5dd}
@media (prefers-color-scheme:dark){:root{--bg:#121212;--carte:#1e1e1e;--texte:#f2f2f2;--doux:#a0a0a0;--bord:#2e2e2e;--bulle-moi:#1f4d2e;--bulle-moki:#262626;--fond-chat:#0e1512}}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;background:var(--bg);color:var(--texte)}
a{color:var(--orange-fonce);text-decoration:none}a:hover{text-decoration:underline}
header{background:var(--carte);border-bottom:1px solid var(--bord);position:sticky;top:0;z-index:5}
.barre{max-width:1100px;margin:auto;padding:12px 16px;display:flex;align-items:center;gap:20px;flex-wrap:wrap}
.logo{font-weight:800;font-size:18px;display:flex;align-items:center;gap:8px;color:var(--texte)}
.logo i{background:linear-gradient(135deg,var(--violet),#9f90ff);color:#fff;width:28px;height:28px;border-radius:8px;display:grid;place-items:center;font-style:normal;font-size:15px}
nav{display:flex;gap:4px}nav a{padding:6px 12px;border-radius:999px;color:var(--doux);font-weight:600}
nav a.actif{background:var(--orange);color:#fff}nav a:hover{text-decoration:none;background:var(--bord)}nav a.actif:hover{background:var(--orange)}
main{max-width:1100px;margin:auto;padding:20px 16px 48px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:28px 0 10px}.sous{color:var(--doux);margin:0 0 18px}
.grille{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}
.carte{background:var(--carte);border:1px solid var(--bord);border-radius:14px;padding:16px}
.stat b{display:block;font-size:26px;line-height:1.2}.stat span{color:var(--doux);font-size:13px}
.stat.alerte b{color:var(--rouge)}.stat.ok b{color:var(--vert)}
table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:10px 12px;border-bottom:1px solid var(--bord)}
th{color:var(--doux);font-size:12px;text-transform:uppercase;letter-spacing:.04em}tr:last-child td{border-bottom:0}
.tableau{overflow-x:auto;padding:0}
.pastille{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;font-weight:700;background:var(--bord)}
.pastille.rouge{background:#fde8e8;color:var(--rouge)}.pastille.ambre{background:#fff4d6;color:#8a6100}.pastille.vert{background:#e3f4e5;color:var(--vert)}
.vide{color:var(--doux);padding:20px;text-align:center}
.chat{background:var(--fond-chat);border-radius:14px;padding:14px;height:62vh;min-height:320px;overflow-y:auto;display:flex;flex-direction:column;gap:8px}
.bulle{max-width:min(78%,520px);padding:8px 12px;border-radius:12px;white-space:pre-wrap;word-wrap:break-word;box-shadow:0 1px 1px rgba(0,0,0,.08)}
.bulle.moi{align-self:flex-end;background:var(--bulle-moi);border-top-right-radius:2px}
.bulle.moki{align-self:flex-start;background:var(--bulle-moki);border-top-left-radius:2px}
.bulle small{display:block;color:var(--doux);font-size:11px;text-align:right;margin-top:2px}
.saisie{display:flex;gap:8px;margin-top:10px}
.saisie input,.saisie select{flex:1;padding:12px 16px;border-radius:999px;border:1px solid var(--bord);background:var(--carte);color:var(--texte);font:inherit}
.saisie select{flex:0 0 auto}
button{background:var(--orange);color:#fff;border:0;border-radius:999px;padding:0 22px;font:inherit;font-weight:700;cursor:pointer}
button:hover{background:var(--orange-fonce)}button:disabled{opacity:.5;cursor:wait}
.puces{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}.puces button{background:var(--carte);color:var(--texte);border:1px solid var(--bord);padding:6px 12px;font-weight:600;font-size:13px}
.journal li{font-family:ui-monospace,Consolas,monospace;font-size:12.5px;color:var(--doux);margin:2px 0}
.deux{display:grid;grid-template-columns:2fr 1fr;gap:16px}@media(max-width:800px){.deux{grid-template-columns:1fr}}
"""


def page(titre: str, corps: str, actif: str = "") -> str:
    liens = [("/console", "Tableau de bord", "tableau"), ("/console/simulateur", "Simulateur", "simulateur")]
    nav = "".join(f'<a href="{h}" class="{"actif" if k == actif else ""}">{t}</a>' for h, t, k in liens)
    return (
        '<!doctype html><html lang="fr"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{escape(titre)} · Moki</title><style>{CSS}</style></head><body>"
        f'<header><div class="barre"><a class="logo" href="/console"><i>✦</i>Moki <span style="color:var(--doux);font-weight:500">console</span></a><nav>{nav}</nav></div></header>'
        f"<main>{corps}</main></body></html>"
    )


def stat(valeur: object, libelle: str, classe: str = "") -> str:
    return f'<div class="carte stat {classe}"><b>{escape(str(valeur))}</b><span>{escape(libelle)}</span></div>'


def pastille(texte: str, couleur: str = "") -> str:
    return f'<span class="pastille {couleur}">{escape(texte)}</span>'


def tableau(entetes: list[str], lignes: list[list[str]], vide: str) -> str:
    if not lignes:
        return f'<div class="carte vide">{escape(vide)}</div>'
    tete = "".join(f"<th>{escape(e)}</th>" for e in entetes)
    corps = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in ligne) + "</tr>" for ligne in lignes)
    return f'<div class="carte tableau"><table><tr>{tete}</tr>{corps}</table></div>'


def bulle(texte: str, moi: bool, heure: str = "") -> str:
    h = f"<small>{escape(heure)}</small>" if heure else ""
    return f'<div class="bulle {"moi" if moi else "moki"}">{escape(texte)}{h}</div>'


SCRIPT_SIMULATEUR = """
const chat=document.getElementById('chat'),champ=document.getElementById('texte'),pme=document.getElementById('pme'),bouton=document.getElementById('envoyer');
function ajoute(t,moi){const d=document.createElement('div');d.className='bulle '+(moi?'moi':'moki');d.textContent=t;chat.appendChild(d);chat.scrollTop=chat.scrollHeight}
async function envoie(t){t=t.trim();if(!t)return;ajoute(t,true);champ.value='';bouton.disabled=true;
try{const r=await fetch('/console/simuler',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({pme_id:+pme.value,texte:t})});
const j=await r.json();if(!r.ok){ajoute('Erreur : '+(j.detail||r.status),false)}else{j.reponses.forEach(x=>ajoute(x,false))}}
catch(e){ajoute('Erreur réseau',false)}bouton.disabled=false;champ.focus()}
document.getElementById('formulaire').addEventListener('submit',e=>{e.preventDefault();envoie(champ.value)});
document.querySelectorAll('.puces button').forEach(b=>b.addEventListener('click',()=>envoie(b.dataset.t)));
ajoute("Salut ! Je suis Moki. Écris-moi comme sur WhatsApp : « j'ai vendu 3 paires à 5000 ».",false);
"""
