For å forbedre dokumentet slik at det kan inngå i en kravspesifikasjon for et programsystem, kan innholdet struktureres og detaljeres ytterligere med fokus på funksjonelle og ikke-funksjonelle krav.
Her er et utkast til en slik forbedring:
--------------------------------------------------------------------------------
Kravspesifikasjon: ImaLink Digital Bildehåndteringssystem
1. Innledning
Denne spesifikasjonen beskriver kravene til ImaLink, et programsystem for effektiv håndtering og organisering av store digitale bildesamlinger. Systemet tar sikte på å løse de utfordringene som oppstår med den massive flommen av bilder i dagens digitale landskap.
1.1. Bakgrunn og Motivasjon
Dagens teknologiske utvikling har resultert i en enorm mengde bilder, hvorav mange er øyeblikksfangster som raskt forsvinner eller blir vanskelige å finne igjen. Selv om skytjenester tilbyr automatisk organisering, har de ulemper som høye kostnader for store samlinger, vanskeligheter med nedlasting av hele samlinger, varierende personvern og potensiell nedskalering eller metadataendring. Profesjonelle verktøy som Adobe krever økonomisk investering og opplæring, noe som gjør dem uegnet for den vanlige bruker. Manuell lagring er en levedyktig løsning, men krever IT-kunnskap og interesse.
ImaLink er basert på erfaringer med manuell lagring, som anses som den beste løsningen. Systemet skal muliggjøre en strukturert lagring av bilder, tilsvarende et negativkatalogsystem, hvor råfiler eller fullstørrelses JPEG-bilder fungerer som "originaler". Målet er å skape et system som håndterer hundretusenvis av bilder (over en terabyte med materiale) og reduserer lagringsbehovet på arbeidsdisken ved å arkivere originalfiler på eksterne medier og eksportere nedskalerte kopier for daglig bruk.
1.2. Mål med Systemet
• Effektiv organisering: Tilby en strukturert metode for lagring og gjenfinning av digitale bilder.
• Redusert lagringsbehov: Muliggjøre arkivering av originalfiler på eksterne medier og tilgang til nedskalerte kopier for daglig bruk.
• Enkel tilgang og søk: Gi et intuitivt grensesnitt for søk, filtrering og visning av bilder.
• Bevaring av originalitet: Håndtere utfordringen med å skille kopi fra original og unngå duplikater.
• Fleksibilitet: Støtte både profesjonelle behov og vanlige brukeres behov.
2. Overordnede Krav
2.1. Funksjonelle Krav
Systemet skal:
• FR1. Databaserte bildehåndtering:
    ◦ FR1.1. Inneholde en sentral database som lagrer all tilgjengelig informasjon om bildene og deres lagringsmedium for originalene.
    ◦ FR1.2. Automatisk hente ut og lagre EXIF-data fra moderne bilder inn i databasen.
    ◦ FR1.3. Tillate manuell inntasting av viktig informasjon som dato og sted for bilder uten EXIF-data (f.eks. skannede bilder).
• FR2. Bildeidentifikasjon og versjonering:
    ◦ FR2.1. Generere en universell ID for hvert bilde, som er nøkkelen for å hente ut en bestemt bildeversjon.
    ◦ FR2.2. Automatisk generere nedskalerte versjoner (f.eks. ca. 1000 piksler) fra masterbildet, lagre dem i filsystemet med navn basert på ID og størrelse (f.eks. "xxxx-medium.jpg"), og lagre stien i databasen.
    ◦ FR2.3. Tillate registrering av nye bildeversjoner (f.eks. etter redigering i et fotoprogram), der bildets ID kan legges inn i filnavnet ved uthenting for redigering.
    ◦ FR2.4. Generere en thumbnail fra masterbildet og lagre denne i databasen for raskere visning.
    ◦ FR2.5. Generere en hash fra thumbnailen for universelle oppslag.
• FR3. Brukergrensesnitt for søk og organisering (Web-basert):
    ◦ FR3.1. Tilby et web-basert brukergrensesnitt for søk i store bildesamlinger.
    ◦ FR3.2. Muliggjøre søk basert på sted og dato.
    ◦ FR3.3. Tillate brukeren å legge til ekstra informasjon (tagger) som lagres i databasen.
    ◦ FR3.4. Gi mulighet til å markere bilder som "public" eller "private".
    ◦ FR3.5. Tillate tillegg av bildetekst og rating.
    ◦ FR3.6. Støtte gruppering av relaterte bilder (f.eks. "serie", "motiv", "panorama") med mulighet for manuell gruppering og støttefunksjoner (f.eks. valg av første og siste bilde i en serie). Databasen må lagre informasjon for å vise en gruppe som ett utvalgt bilde.
• FR4. Album- og publiseringsfunksjonalitet:
    ◦ FR4.1. Tilby funksjonalitet for å lage albumer.
    ◦ FR4.2. Basere albumer på Markdown for minimalt plassbehov og lagring i databasen.
    ◦ FR4.3. Bruke albumer for lysbildeserier, fotobøker eller blogginnlegg.
• FR5. Kildehåndtering og Import:
    ◦ FR5.1. Støtte import av bilder fra en katalog på disk ("kilde").
    ◦ FR5.2. Ved opplasting av ny kilde, kreve obligatorisk spesifisering av forfatter (som skal ha en egen tabell i databasen).
    ◦ FR5.3. Tillate tillegg av notater for å beskrive mediet kilden ligger på (f.eks. ekstern harddisk).
    ◦ FR5.4. Tilby en strategi for å initialisere manglende EXIF-informasjon (f.eks. hente årstall og dato fra foreldrekatalogens navn).
    ◦ FR5.5. Gi mulighet til å oppdatere en "innhold.json"-fil på kildemediet før opplasting for automatisk deteksjon av kilden.
    ◦ FR5.6. Skalle kildekatalogen for bildefiler, registrere hver fil som et objekt i en "filer"-tabell.
    ◦ FR5.7. Detektere og håndtere rå-format og JPEG-versjoner av samme bilde, med mulighet for å spesifisere håndtering via "innhold.json".
    ◦ FR5.8. Opprette et element i en "bilder"-tabell for hvert bilde, med referanse til en eller to filer (JPEG eller RAW), og velge en "master" basert på en brukerdefinert regel (f.eks. JPEG hvis tilgjengelig, ellers RAW).
2.2. Ikke-funksjonelle Krav
2.2.1. Ytelse
• NFR1.1. Skalerbarhet: Kjernen og brukergrensesnittet må være lett å utvide for å håndtere store mengder data (hundretusenvis av bilder, over en terabyte) og brukere.
• NFR1.2. Responstid: Raske oppslag og enkel redigering av brukerdata skal være mulig gjennom databasebruk.
2.2.2. Brukbarhet
• NFR2.1. Intuitivitet: Brukergrensesnittet må være enkelt og intuitivt å bruke.
• NFR2.2. Klart design: Startsiden skal være klar og tydelig med logisk plassering av navigasjonsverktøy.
• NFR2.3. Grunnleggende verktøy: Inkludere browser, viewer for bilder, og en WYSIWYG Markdown editor.
• NFR2.4. Modusstyring: Skille mellom en privat redigeringsmodus og en offentlig visningsmodus.
2.2.3. Sikkerhet
• NFR3.1. Tilgangsstyring: Tilgang til data må være styrt av brukerrettigheter.
2.2.4. Vedlikeholdbarhet og Utvikling
• NFR4.1. Dokumentasjon: Programkoden skal være veldokumentert og lett forståelig for nye programmerere.
• NFR4.2. Arkitektur: Kjerne og brukergrensesnitt skal være separate deler.
• NFR4.3. API-struktur: API-et skal være strukturert slik at det passer sømløst med brukergrensesnittet uten unødvendig funksjonalitet.
• NFR4.4. Standardisering: Bruke veldokumenterte verktøy og programbiblioteker på en mest mulig standardisert måte.
• NFR4.5. Utvidbarhet: Database og API må være lett å utvide uten å gjøre koden uoversiktlig.
2.2.5. Teknologiske Krav
• NFR5.1. Kjerne-teknologi: Kjernen bør være API-basert.
• NFR5.2. UI-teknologi: Brukergrensesnittet bør være web-basert.
• NFR5.3. Programmeringsspråk: Foretrukket utvikling i Python for kjernen. JavaScript kan vurderes for brukergrensesnittet der det er hensiktsmessig.
• NFR5.4. AI-integrasjon (utvikling): Det skal være mulig å bruke AI til å holde oversikt over programstruktur og kildefiler, samt arbeide interaktivt med AI for å komme frem til en fungerende programstruktur.
3. Systemarkitektur (Konseptuell)
Systemet skal bestå av følgende hovedkomponenter:
• 3.1. Kjernen (Backend):
    ◦ Database: Fundamentet for raske oppslag og enkel redigering av brukerdata.
    ◦ Filstruktur: Designet for å lagre store mengder små bildefiler.
    ◦ API: Gir grensesnitt for kommunikasjon med brukergrensesnittet og håndterer forretningslogikk og datatilgang.
• 3.2. Brukergrensesnittet (Frontend):
    ◦ Web-basert applikasjon: Sørger for interaksjon med brukeren.
    ◦ GUI-komponenter: Robuste og enkle komponenter for visning og redigering.
4. Innledende Brukstilfelle (Arbeidsflyt)
Følgende innledende arbeidsflyt skal implementeres som et demonstrasjons- og testcase:
4.1. Manuelle Forberedelsessteg:
1. Brukeren kopierer manuelt bilder fra et minnekort til en katalog på disk, og sletter deretter minnekortet.
2. Brukeren organiserer manuelt filene i katalogen i underkataloger med navn som "ÅÅÅÅ_MM_DD_tittel".
4.2. System-assisterte Steg:
3. Brukeren starter ImaLink brukergrensesnittet og velger katalogen med bilder ("kilde").
4. Brukeren initierer en "Legg til"-prosess, som gir mulighet til å legge til ekstra informasjon før data legges inn i databasen.
5. Databasen registrerer en opplasting som peker til "kilde"-katalogen. Katalogen kan inneholde en "innhold.json"-fil med instruksjoner for kjernen.
6. Kjernen scanner "kilde"-katalogen for bildefiler. Hver fil registreres som et objekt i tabellen "filer". Programmet skal detektere om rå-formatfiler og JPEG-filer ligger side om side for samme bilde, og "innhold.json" kan gi instruksjoner for håndtering.
7. Det opprettes en tabell "bilder" med objekter som peker til ett eller flere objekter i "filer" (for eksempel JPEG eller RAW).
8. For hver fil opprettes et element i tabellen "exif" dersom slike data finnes, og et utvalg verdier hentes for raskere tilgang.
9. For hvert bilde i "bilder"-tabellen:
    ◦ Det opprettes en referanse til en eller to filer (JPEG eller RAW).
    ◦ Én fil velges som "master" basert på en brukerdefinert regel (f.eks. JPEG hvis tilgjengelig, ellers RAW).
    ◦ En liten thumbnail genereres fra masterbildet og legges inn i databasen.
    ◦ En hash genereres fra thumbnailen og brukes for universelt oppslag.
    ◦ En nedskalert versjon (ca. 1000 piksler, "medium") genereres og legges i filsystemet med navnet "<id>-<størrelse>.jpg" (f.eks. "xxxx-medium.jpg"). Stien til denne filen skal kunne hentes via databasen.
10. Ved opplasting av ny kilde, skal brukeren spesifisere:
    ◦ Forfatter: Den obligatoriske forfatteren for bildene i kilden (lagres i egen tabell).
    ◦ Notater: Eventuell beskrivelse av mediet kilden ligger på (f.eks. ekstern harddisk).
    ◦ Strategi for EXIF-initialisering: En regel for å fylle inn manglende EXIF-informasjon (f.eks. årstall og dato fra overordnet katalognavn for skannede bilder).
11. Systemet skal gi mulighet for å oppdatere "innhold.json" på kildemediet før opplasting, for automatisk deteksjon av kilder på tilkoblede, skrivbare medier.
--------------------------------------------------------------------------------
