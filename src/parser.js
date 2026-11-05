// Passage parser. Pure functions only (no DOM) so it can be tested in Node.
// The sentence/chunk split MUST stay identical to parse() in tools/gen_audio.py;
// tests/parser.test.mjs + tests/test_parser_parity.py check this against data/problems.json.
//
// Input format: "/" separates chunks, a line starting with "=" is the Japanese
// translation of the previous line, "TITLE:" (or "# ") is the title, and lines
// after "WORDS:" are glossary entries ("word = meaning").
export function splitSentences(line){
  return line.split(/(?<=[.!?]["”’)]?)\s+(?=["“‘(]?[A-Z0-9])/).map(x=>x.trim()).filter(Boolean);
}
export function parse(raw){
  const lines=String(raw||'').replace(/\r/g,'').split('\n');
  let title='', mode='body'; const units=[], words={};
  for(let L of lines){
    const line=L.trim(); if(!line||/^-{3,}$/.test(line)||/^```/.test(line))continue;
    let m;
    if(mode==='body'&&(m=line.match(/^(?:TITLE\s*[:：]|#\s+)(.+)$/i))){title=m[1].trim();continue}
    if(/^(?:#+\s*)?(WORDS|VOCAB(ULARY)?|語注|単語)\s*[:：]?$/i.test(line)){mode='words';continue}
    if(mode==='words'){
      m=line.match(/^[-・*]?\s*(.+?)\s*(?:=|＝|:|：|\t)\s*(.+)$/);
      if(m)words[m[1].toLowerCase().trim()]=m[2].trim();
      continue;
    }
    if(/^[=＝]/.test(line)){ if(units.length)units[units.length-1].ja=(units[units.length-1].ja?units[units.length-1].ja+' ':'')+line.replace(/^[=＝]\s*/,''); continue}
    units.push({en:line,ja:''});
  }
  const sentences=[];
  for(const u of units){
    const pieces=u.ja?[u.en]:splitSentences(u.en);
    for(const p of pieces){
      const chunks=p.split(/\s+\/\s+|\s*\/\s*(?=\S)/).map(x=>x.trim()).filter(Boolean);
      if(!chunks.length)continue;
      const offsets=[];let o=0;chunks.forEach(c=>{offsets.push(o);o+=c.length+1});
      sentences.push({chunks,offsets,text:chunks.join(' '),ja:u.ja});
    }
  }
  if(!title&&sentences.length){title=sentences[0].text.split(/\s+/).slice(0,6).join(' ')+'…'}
  return {title,sentences,words};
}
export const countWords=s=>s.split(/\s+/).filter(w=>/[A-Za-z0-9]/.test(w)).length;
