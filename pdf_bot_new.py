
import sys
import re
import pypdf

PDF_PATH = "the_constitution_of_india.pdf"

def load_articles(pdf_path):
    articles = {}
    try:
        reader = pypdf.PdfReader(pdf_path)
    except Exception as e:
        print(f"Error reading PDF: {e}")
        sys.exit(1)

    # Regex patterns
    
    # Article start: "1. Name...", "21. Protection..."
    # Handles footnote prefixes: "3[21A. Right..." or "21A."
    # Group 1: Optional prefix like "3["
    # Group 2: Article Number like "21A"
    # Group 3: Title and potentially start of text
    art_pattern = re.compile(r'^(\d+\[)?(\d+[A-Z]?)\.\s+(.*)')
    
    # Footnote/Noise patterns to IGNORE
    # 1. Subs. by...
    # 2. Ins. by...
    # 3. 1. Clauses were omitted... (Common in official PDF footnotes)
    # We check if the content contains "Amendment) Act" or starts with specific words
    footnote_keywords = ['Subs.', 'Ins.', 'Omitted', 'Rep.', 'Added', 'Substituted', 'Inserted']
    footnote_regex = re.compile(r'^\d+\.\s+(' + '|'.join(footnote_keywords) + ')')

    # Structure headers to STOP accumulation (Parts/Chapters)
    structure_pattern = re.compile(r'^(\d+\[)?(PART\s+[IVXLC]+|CHAPTER\s+[IVXLC]+)')

    current_art_num = None
    current_art_text = []

    # Start scanning from page 20 
    start_page_index = 20 
    seen_articles = set()

    for i in range(start_page_index, len(reader.pages)):
        page = reader.pages[i]
        text = page.extract_text()
        if not text:
            continue
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 1. Check for Structure Header -> STOP current article accumulation
            if structure_pattern.match(line):
                if current_art_num:
                    articles[current_art_num] = "\n".join(current_art_text).strip()
                    current_art_num = None
                    current_art_text = []
                continue

            # 2. Check for Article Start
            match = art_pattern.match(line)
            if match:
                prefix = match.group(1)
                art_num_candidate = match.group(2)
                content_part = match.group(3)

                # HEURISTIC: Filter Footnotes
                # a) Matches explicit footnote pattern
                if footnote_regex.match(line):
                    continue
                # b) Contains "Amendment) Act" or "w.e.f." (With Effect From)
                if "Amendment) Act" in content_part or "w.e.f." in content_part:
                    continue
                # c) Very short line or doesn't have any letters
                if not re.search(r'[A-Za-z]', content_part):
                    continue
                
                # HEURISTIC: First-Come First-Served
                # Articles 1-395 appear once in the body sequentially.
                # Once we've seen an article number, any further line starting with it is likely a footnote.
                if art_num_candidate in seen_articles:
                    continue
                
                # New Article found!
                # Save previous
                if current_art_num:
                    articles[current_art_num] = "\n".join(current_art_text).strip()
                
                # Start new
                current_art_num = art_num_candidate
                seen_articles.add(current_art_num)
                current_art_text = [content_part]
            
            else:
                # Continuation of current article
                if current_art_num:
                    # Ignore page numbers
                    if re.match(r'^\d+$', line):
                        continue
                    # Ignore weird page artifacts
                    if re.match(r'^\d+\s+\d+$', line): 
                        continue
                    
                    # Optional: Stop if line looks like it starts a DIFFERENT article number but was missed?
                    # No, we rely on the logic above to find starts.
                    
                    current_art_text.append(line)

    # Save last one
    if current_art_num:
        articles[current_art_num] = "\n".join(current_art_text).strip()
            
    return articles

def get_answer(query, articles):
    q = query.strip().lower()
    
    # Check for "Article X" pattern
    match = re.search(r'(?:article|art\.?)\s*(\d+[a-z]?)', q)
    if match:
        key = match.group(1).upper() 
        if key in articles:
            return f"Article {key}\n\n{articles[key]}"
        else:
            return "The requested article is not found in the document."
            
    if re.match(r'^\d+[a-z]?$', q):
        key = q.upper()
        if key in articles:
             return f"Article {key}\n\n{articles[key]}"
        else:
             return "The requested article is not found in the document."

    # If it's a general question, the rules say:
    # "If the question goes beyond what the Article states, reply: 'The document does not contain this information.'"
    # But usually users ask about a topic.
    # For now, stay strict to Article numbers as per previous instructions.
    return "The document does not contain this information."

if __name__ == "__main__":
    # For simple CLI testing
    if len(sys.argv) > 1:
        # Load and answer once
        arts = load_articles(PDF_PATH)
        print(get_answer(" ".join(sys.argv[1:]), arts))
    else:
        # Regular main loop as before
        from pdf_bot import main
        main()
