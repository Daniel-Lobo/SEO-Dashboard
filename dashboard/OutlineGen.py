from aiohttp import ClientSession
from os import getenv, system
from bs4 import BeautifulSoup
from html import unescape
from asyncio import gather
from dashboard.constants import PROMPT
from dashboard.ChatGpt import ACompletion, AChat, OpenRouterAChat  #type: ignore
from re import findall 
from flask import request

def ExtractTagedText(text):    
    pattern = r"<([^>]+)>([\s\S]*?)<\/\1>"    
    matches = findall(pattern, text)       
    if len(matches) == 0: return text
    return ''.join([match[1] + '\n' for match in matches])
async def serp(contry_code: str, keyword: str):      
    keyword = keyword.strip()
    keyword = keyword.replace('  ', ' ')
    keyword = keyword.replace(' ', '+')
    domain  = {'us' : 'google.com', 'ca' : 'google.ca', 'uk' : 'google.co.uk', 'au' : 'google.co.au', 'nl' : 'google.nl'}[contry_code.lower()]
    lang    = 'lang_en' #'lang_nl' if country == 'nl' else 'lang_en'
    url     = f'https://api.valueserp.com/search?api_key={getenv("VALUE_SERP_API_KEY")}&lr={lang}&country_code={contry_code}&q={keyword}&google_domain={domain}&gl={contry_code}&page=1&max_page=1&num=11'
    try:
        async with ClientSession() as session:
             async with session.get(url) as response:           
                if response.status == 200: 
                    json = await response.json()    
                    return [item['link'] for item in json['organic_results']]                 
                else:                        
                    return [f'Response.status == {response.status } Caling SERP API']      
    except Exception as e:            
        return [f'Exception: "{e}" Caling SERP API']

def parseoutline(soup):         
        h1             = 0
        h2             = 0
        h3             = 0
        h4             = 0
        outline        = ''
        for item in soup.find_all():            
            tx  = unescape(item.text).strip('\n').strip('\r')
            if item.name.lower() == 'h2': 
                h2             += 1  
                outline        += f'{h2} . {tx}\n'                
                h3             = 0
                h4             = 0  
            if item.name.lower() == 'h3': 
                if h2==0: continue
                h3             += 1  
                outline        += f'  {h2}.{h3} {tx}\n'                
                h4             = 0
            if item.name.lower() == 'h4': 
                if h3==0: continue
                h4             += 1 
                outline        += f'\t{h2}.{h3}.{h4} {tx}\n'
        return outline    

async def AsyncFishScrapeURL(url: str, _1st_try=True): 
        fish_key = 'qIg2guLzeGt2StEwFwT7lvzw0PBVNnq1xcJOWknam4AfRdvDGntmjQGhWOFakXhoE3AXNrykaF5bPWRGRF'    
        request  = f'https://scraping.narf.ai/api/v1/?api_key={fish_key}&url={url}&render_js=true&total_timeout_ms=110000'    
        request  = f'https://scraping.narf.ai/api/v1/?api_key={fish_key}&url={url}&render_js=true'              
        try:              
            async with ClientSession() as session:
                async with session.get('https://scraping.narf.ai/api/v1/', params={'api_key': fish_key, 'url': url,
                                       'total_timeout_ms' : 100_000, 'trial_timeout_ms' : 30_000}) as response:           
                    if response.status == 200: 
                        text = await response.text()                       
                        return parseoutline(BeautifulSoup(text, 'html.parser'))
                    elif response.status == 429:
                        return await AsyncFishScrapeURL(url, True)
                    else:   
                        if _1st_try == True: return await AsyncFishScrapeURL(url, False)                          
                        return f'Response.status == {response.status } scraping {url}'                
        except Exception as e:
            return f'Eception scraping url:\n{e}'       


def SplitURL(urls):
    chunks = [[]]
    for url in urls:
        if len(chunks[-1]) == 24: chunks.append([])
        chunks[-1].append(url)
    return chunks     

async def ScrapeURLs(URLs):
    urls_chunks = SplitURL(URLs)
    reply = []
    for chunk in urls_chunks:
        reply.extend(await gather(*[AsyncFishScrapeURL(url) for url in chunk]))
    return reply   

    return await gather(*[AsyncFishScrapeURL(url) for url in URLs])  

def extract_questions_and_answers(data):
    questions = data.get("related_questions", [])
    qa_list   = []
    for qa in questions:
        question = qa.get("question", "")
        answer   = qa.get("answer", "")
        qa_list.append(f"Question: {question}\nAnswer: {answer}\n\n")
    return "\n".join(qa_list)

def extract_featured_snippet(data):
    answers          = data.get("answer_box", {}).get("answers", [])
    featured_snippet = "No featured snippet found."
    if answers:
        answer = answers[0].get("answer", "")
        steps  = answers[0].get("steps", [])
        if steps:
            featured_snippet = f"{answer}\n" + "\n".join([f"- {step}" for step in steps])
        else:
            featured_snippet = answer
    return featured_snippet

async def fetch_value_serp_data(keyword, country):
    api_key = getenv('VALUE_SERP_API_KEY')
    domain  = {'us' : 'google.com', 'ca' : 'google.ca', 'uk' : 'google.co.uk', 'au' : 'google.co.au', 'nl' : 'google.nl'}[country.lower()]
    lang    = 'lang_en' #'lang_nl' if country == 'nl' else 'lang_en'
    url = f"https://api.valueserp.com/search?api_key={api_key}&lr={lang}&country_code={country}&q={keyword}&page=1&max_page=1&google_domain={domain}&gl={country}&hl=en&device=desktop&include_answer_box=true"
   
    async with ClientSession() as session:
         async with session.get(url) as response:
            if response.status == 200: 
                json = await response.json()                       
                return json
            else:                                
                return None             

async def analyze_search_intent_with_openai(keyword, featured_snippet, questions_and_answers, model, Prompt):
    if Prompt == None:
        prompt = PROMPT.GEN_SEARCH_INTENT.format(keyword, featured_snippet, questions_and_answers)
    else:
        tags   = {'{KEYWORD}' : keyword, '{FEATURED_SNIPPET}' : featured_snippet, '{QANDA}' : questions_and_answers}
        prompt = Prompt
        for tag, value in tags.items():
            prompt = prompt.replace(tag, value)         
    return await ACompletion(prompt, model=model)        

async def GenSearchIntent(country, keyword, model, prompt):
    print(f'Generating Search Intent for keyword: {keyword}, country_code: {country}')
    try:       
        value_serp_data = await fetch_value_serp_data(keyword, country)
        if value_serp_data is None:
            return 'Failed to fetch data from ValueSERP API'
        else:            
            featured_snippet             = extract_featured_snippet(value_serp_data)           
            questions_and_answers        = extract_questions_and_answers(value_serp_data)                         
            return await analyze_search_intent_with_openai(keyword, featured_snippet, questions_and_answers, model, prompt)                               
    except Exception as e:
        return f'Exception {e}'  

async def GenerateOutlineMistral(keyword, outlines, intent, semantic_analisys, model, tones, audience, dbug=False):
    outlines_prompt = ''.join([f'Article #{n+1}:\n{article}\n' for n, article in enumerate(outlines)])
    user            =  PROMPT.GEN_OUTLINE_MISTRAL_USER.format(keyword, outlines_prompt, intent, semantic_analisys)
    msgs            = [{'role': 'system', 'content': PROMPT.GEN_OUTLINE_MISTRAL_SYSTEM}, {'role': 'user', 'content': user}]
    if dbug: return PROMPT.GEN_OUTLINE_MISTRAL_SYSTEM + "\n" + user
    return await OpenRouterAChat(msgs, model=model, temp=0.3)

async def GenerateOutline(keyword: str, search_intent: str, outlines: list[str], model):
    count           = len(outlines)  
    outlines_prompt = ''.join([f'Article #{n+1}:\n{article}\n' for n, article in enumerate(outlines)])
    prompt          = PROMPT.GEN_OUTLINE.format(keyword, count, outlines_prompt, search_intent)  
    return await OpenRouterAChat([{'role' : 'user', 'content' : prompt}], model=model, temp=0.2, top_p=0.7)   # ACompletion(prompt, temp=0.2, top_p=0.7)  

def GetCleanOutline(raw: str)->str:
    close_tag = raw.find('</outline_cleaned>')
    open_tag  = raw.find('<outline_cleaned>')
    if close_tag > open_tag and open_tag > -1:
        return raw.split('<outline_cleaned>')[1].split('</outline_cleaned>')[0]
    return raw 

async def CleanUPOutline(keyword, old_outline, model):
    system = request.json['System'].replace('{KEYWORD}', keyword).replace('{OUTLINE}', old_outline)
    user   = request.json['User'].replace('{KEYWORD}', keyword).replace('{OUTLINE}', old_outline)   
    msgs   = [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]
    return GetCleanOutline(await OpenRouterAChat(msgs, model=model, temp=0.2)) 

async def GenerateOptmizedOutlineWithFacts(keyword, outlines, intent, semantic_analisys, facts, tones, audience, model, prompts, instructions, dbug=False):
    if len(outlines) == 0: outlines_prompt = '\nNo competitor\'s outlines were found.\n'
    else                 : outlines_prompt = ''.join([f'Article #{n+1}:\n{article}\n' for n, article in enumerate(outlines)])    
    facts           = f'Factual Information:\n{facts}' if facts != '' else ''
    tones           = f'the tone "{tones[0]}" ' if len(tones) < 2 else f'a mix of the tones: "{tones[0]}" and "{tones[1]}"'
    #system          =  PROMPT.GEN_OUTLINE_BETTER_SYSTEM.format(audience, tones)
    #user            =  PROMPT.GEN_OUTLINE_BETTER_USER.format(keyword, outlines_prompt, intent, semantic_analisys, facts)    
    user            = prompts['Outline User']
    system          = prompts['Outline System']
    for tag, value in {'{KEYWORD}' : keyword, '{OUTLINES}' : outlines_prompt, '{INTENT}' : intent, '{SEMANTIC_ANALYSIS}' : semantic_analisys, 
    '{SPECIAL_INTRUCTIONS}' : 'Special Instructions:\n'+instructions, '{FACTS}' : facts, '{TONES}' : tones, 
    '{COMPETITORS_OUTLINES}' : outlines_prompt, '{AUDIENCE}' : audience[0]}.items():        
        user   = user.replace(tag, value)
        system = system.replace(tag, value)
    #print(system) 
    #print(user)   
    msgs = [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]
    if dbug: return system + "\n" + user
    #return system + "\n" + user
    return ExtractTagedText(await OpenRouterAChat(msgs, model=model, temp=0.3))

    return 'Outline with facts placeholder'   

async def GenerateOptmizedOutline(keyword, outlines, intent, semantic_analisys, tones, audience, model, dbug=False):    
    #if model == 'mistralai/mistral-medium': return await GenerateOutlineMistral(keyword, outlines, intent, semantic_analisys, tones, audience, dbug)
    if model != 'openai/gpt-4-turbo-preview': return await GenerateOutlineMistral(keyword, outlines, intent, semantic_analisys, model, tones, audience, dbug)
    if len(tones) == 1:
        system_1 = PROMPT.GEN_OPTMIZED_OUTLINE_SYSTEM_1.format(
            f'if necessary. Maintain a "{tones[0]}" tone and tailor the content for the audience "{audience}".',
            intent, semantic_analisys 
        )
        user_2 = PROMPT.GEN_OPTMIZED_OUTLINE_USER_2.format(keyword, f'Remember to Maintain a "{tones[0]}" tone.')
    else: 
        system_1 = PROMPT.GEN_OPTMIZED_OUTLINE_SYSTEM_1.format(
            f'if necessary. Maintain a mix of "{tones[0]}" and "{tones[1]}" tones and tailor the content for the audience "{audience}".',
            intent, semantic_analisys 
        )  
        user_2 = PROMPT.GEN_OPTMIZED_OUTLINE_USER_2.format(keyword, f'Remember to Maintain a mix of "{tones[0]}" and "{tones[1]}" tone.')

    user_1 = f'Keyword: {keyword}\n\n'
    for i, outline in enumerate(outlines):
        user_1 += f'Article #{i} Outline:\n{outline}\n\n'        

    user_1 += f'Search Intent Analysis:\n{intent}\n\nSemantic Analysis:\n{semantic_analisys}'
    if dbug: 
        return 'system 1: ' + system_1 +  '\n\nuser 1: ' + user_1 + '\n\nuser 2:' + user_2

    msgs        = [{'role': 'system', 'content': system_1}, {'role': 'user', 'content': user_1}]
    assistant_1 =  await AChat(msgs, temp=0.3) 
    msgs.append({'role': 'assistant', 'content': assistant_1})
    msgs.append({'role': 'user', 'content': user_2})
    assistant_2 =  await AChat(msgs, temp=0.3) 

    return assistant_1 if 'We’re done!' == assistant_2 else assistant_2[::-1].replace('We’re done!'[::-1], '', 1)[::-1]
    

