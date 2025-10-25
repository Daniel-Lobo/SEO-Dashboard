from sentence_transformers import SentenceTransformer
from sentence_transformers.util import cos_sim
from re import match, sub
from json import dumps
from flask import jsonify
from threading import Thread
from dashboard.content_creator import IpprovedOutlineSectionSpliter

def Trim(string: str) -> str:
    string = string.replace('\n', '').replace('\r', '')   
    return string.strip()    

def GetOutlineSections(outline_arg):
    if outline_arg == '': return []
    secs = IpprovedOutlineSectionSpliter(outline_arg, False)
    return [plain for plain, tagged in zip(secs['Plain'], secs['Tagged']) if not tagged.startswith('Introduction-Tag') and not tagged.startswith('Conclusion-Tag')]
    faq           = 'frequently asked questions'
    new_outline   = ''
    tag           = ':section_start_tag:'
    outline: str  = outline_arg
    exclusion_tag = False
    for line in outline.splitlines():
        line  = Trim(line) 
        found = match(r'-*\s*[*]*\s*[0-9.\s]+', line)
        if found is not None and found.group() != '':                        
            line = sub(r'-*\s*[*]*\s*[0-9.\s]+', tag, line, 1)                
            exclusion_tag = False  
        found = match(r'-*\s*Q[0-9]:', line)
        if found is not None and found.group() != '':                        
            line = sub(r'-*\s*Q[0-9]:', tag, line, 1)               
            exclusion_tag = False                   
        if line.startswith(f'{tag}Introduction')      or line.startswith(f'{tag}Conclusion')         \
            or line.startswith(f'{tag} Introduction') or line.startswith(f'{tag} Conclusion')        \
            or line.startswith('Introduction')        or line.startswith('Conclusion')               \
            or line.lower().startswith(faq)           or line.lower().startswith(f'{tag}{faq}'):
            exclusion_tag  = True    
        if exclusion_tag == False: new_outline += line + '\r\n'
    sections = [s for s in [Trim(string) for string in new_outline.split(tag)] if len(s) and not s.startswith('## TABLE OF CONTENT')]          
    return sections

def InitEmbbeder():     
    g_embeder = SentenceTransformer('msmarco-distilbert-base-v4')  
    print('Embeder initialized') 
g_embeder = SentenceTransformer('msmarco-distilbert-base-v4')  
#Thread(target=InitEmbbeder, args=()).start()       

def EncodeKeywords(kords: dict):
    corpus                    = list(kords.keys())   
    keywords_encodings        = g_embeder.encode(corpus, convert_to_tensor=True) 
    keywords_encodings        = {KeyWord : embedding for KeyWord, embedding in zip(corpus, keywords_encodings)}   
    return keywords_encodings

def ClusterSimilarity(cluster, signal, reply):    
    #print(cluster.keys())
    flat_keywords = [kword for kword, outline in cluster.items()]
    flat_sections = []
    for kword, outline in cluster.items():
        flat_sections.extend(GetOutlineSections(outline))

    flat_trimed   = []
    for section in flat_sections:      
        try: flat_trimed.append(section.split('. ')[1])
        except Exception: flat_trimed.append(section)            

    keywords_encodings = g_embeder.encode(flat_keywords, convert_to_tensor=True) 
    sections_encodings = g_embeder.encode(flat_trimed, convert_to_tensor=True) 
    similarity         = cos_sim(keywords_encodings, sections_encodings)         #type: ignore
    similarity_dict    = {}
    for row, keyword in enumerate(flat_keywords):
        similarity_dict[keyword] = {}
        for column, section in enumerate(flat_sections):
            similarity_dict[keyword][section] = f'{similarity[row][column]:.2f}'

    #print(dumps( similarity_dict, indent=4))        
    unsorted = {}
    for kword, outline in cluster.items():
        unsorted[kword] = []
        for target, target_outline in cluster.items():
            if target == kword: continue
            unsorted[kword].append({'Target' : target, 'Max' : -1.0, 'Sections' : []})
            for section in GetOutlineSections(outline):
                unsorted[kword][-1]['Sections'].append({'Section' : section, 'Similarity' : similarity_dict[target][section]})

    for k, kword in unsorted.items():       
        for target in kword: 
            target['Sections'].sort(reverse=True, key=lambda sim: sim['Similarity'])  
            target['Max'] = target['Sections'][0]['Similarity'] if len(target['Sections']) > 0 else -1.0 

    for k, kword in unsorted.items():  
        kword.sort(reverse=True, key=lambda sim: sim['Max'])          
    
    #print(unsorted)  
    reply          = unsorted
    signal['Done'] = unsorted 
    return unsorted
