# Identity Guardian

Identity Guardian este un toolkit de apărare pentru protecția identității online, care ajută utilizatorii să monitorizeze expunerea datelor personale, să evalueze igiena digitală și să genereze cereri de ștergere a datelor conform GDPR.

## Funcționalități

- **Monitor de Expunere**: Verifică dacă email-urile sau username-urile au fost expuse în breșe de securitate sau pe site-uri precum Pastebin, folosind API-urile HaveIBeenPwned, Google Custom Search, Intelligence X, DeHashed și LeakCheck.
- **Evaluare Igienă Digitală**: Chestionar interactiv pentru a evalua practicile de securitate, cu scoruri și recomandări personalizate generate de Google Gemini API.
- **Anti-Dox Toolkit**: Generează cereri de ștergere a datelor personale (GDPR) pentru diverse platforme, cu template-uri bazate pe modelul ANAF.
- **Dashboard**: Centralizează rapoartele și istoricul verificărilor.

## Cerințe

- Python 3.8+
- Sistem de operare: Windows, macOS sau Linux
- Chei API pentru: HaveIBeenPwned, Google Custom Search, Google Gemini, Intelligence X, DeHashed, LeakCheck (opțional, dar recomandat)

## Instalare

1. **Clonează repository-ul**:
   ```bash
   git clone https://github.com/alexcadar/identity-guardian.git
   cd identity-guardian
   ```

2. **Creează un mediu virtual**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Pe Windows: venv\Scripts\activate
   ```

3. **Instalează dependențele**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurează variabilele de mediu**:
   Creează un fișier `.env` în directorul proiectului și adaugă cheile API:
   ```plaintext
    HIBP_API_KEY="" #Necesita abonament
    GOOGLE_API_KEY="" #Free in google cloud console - https://console.cloud.google.com/apis
    GOOGLE_CSE_ID="" #Free in google cloud console - urmareste documentatia https://support.google.com/programmable-search/answer/12499034?hl=en
    GEMINI_API_KEY="" #Free in google cloud console - https://console.cloud.google.com/apis
    LEAK_CHECK="" #Necesita abonament
    DEHASHED="" #Necesita abonament
    INTELLX="" #versiune free limitata
   ```

5. **Inițializează baza de date**:
   Baza de date SQLite (`identity_guardian.db`) se creează automat la prima rulare.

6. **Rulează aplicația**:
   ```bash
   python app.py
   ```
   Accesează aplicația la `http://localhost:5000` în browser.

## Utilizare

- **Monitor de Expunere**: Introdu un email sau username pentru a verifica expunerea.
- **Igienă Digitală**: Completează chestionarul pentru a primi un raport de securitate.
- **Anti-Dox Toolkit**: Selectează tipurile de date și motivul pentru a genera cereri GDPR.
- **Dashboard**: Vizualizează rapoartele anterioare.

## Note

- Aplicația rulează local, fără a stoca date pe servere externe (cu excepția apelurilor API).
- Asigură-te că fișierul `identity_guardian.log` are permisiuni de scriere.
- Pentru suport, consultă documentația API-urilor utilizate sau contactează echipa de dezvoltare.
