import urllib.request
import sys

def check_html(url):
    print(f"Checking {url}...")
    try:
        with urllib.request.urlopen(url) as response:
            html = response.read().decode('utf-8')
            
            # Check for the static script source
            if 'src="/js/aai.js"' in html or 'src=\'/js/aai.js\'' in html:
                print("FOUND '/js/aai.js' script tag in HTML.")
            else:
                print("ERROR: Could NOT find '/js/aai.js' script tag in HTML.")

            if 'Visão Geral' in html or 'VISÃO GERAL' in html:
                print("CONFIRMED: This is the Index page.")
            
            if 'sidebar' in html.lower():
                 print("Found sidebar in HTML.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_html("http://localhost:3000/")
