import urllib.request
import time

def check_script():
    print("Testando localhost:3000...")
    retries = 3
    for _ in range(retries):
        try:
            req = urllib.request.urlopen('http://localhost:3000')
            html = req.read().decode('utf-8')
            if 'window.actionAIPlayAudio' in html:
                print("VALIDADO: O script está presente nativamente no HTML do servidor!")
                return
            else:
                print("ERRO: Script ausente do HTML.")
                return
        except Exception as e:
            print(f"Buscando... {e}")
            time.sleep(2)
    print("FALHA: Nao conectou.")

if __name__ == "__main__":
    check_script()
