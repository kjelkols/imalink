# ImaLink
Dagens tekniske utvikling har ført til en massiv flom av bilder. Det meste er øyeblikk som fanges og deles før kildematerialet forsvinner i det store sluket før det til slutt blir sendt til resirkulering sammen med den gamle telefonen eller laptopen. Et mindretall er mer systematiske og lagrer bildefilene på en strukturert måte for lettere å finne gamle minner. Mange velger å bruke skytjenester som automatisk organiserer bildene. Fotografer kan bruke profesjonelle verktøy fra f.eks Adobe for å lage en arbeidsstruktur. Det siste krever verktøy som kan kreve økonomisk invsetering og som i tillegg krever opplæring. 

## Utfordringer
Utfordringene er generelt sett kjent for alle

* Vanskelig å skille kopi fra original. Det som før var negativet er nå en bildefil som kan kopieres og endres, til og med uten å endre filnavnet.
* Det som kommer ut av kameraet eller telefonen er en ganske stor fil som ikke egner seg å dele uten skalering.
* Skytjenester har fordeler, men også ulemper
  * Dyrt hvis du har en stor bildesamling
  * Vanskelig å laste ned hele bildesamlinger i ettertid
  * Personvern kan variere
  * Bildene kan ha blitt automatisk nedskalert eller fått endrede metadata
* Proprietære fotoprogrammer er laget for profesjonelle fotografer og bortkastet for den vanlige bruker
* Manuell lagring er en grei løsning for vanlige brukere, men krever kunnskap og interesse for it

## Bakgrunn for ideen
Basert på egne erfaringer er manuell lagring den beste løsningen. Jeg har i mange år hatt et system som kan sammenlignes med en katalog med negativer. Negativene er råfilene fra kameraet. Av og til er disse på jpeg-format, dvs fremkalte originalbilder i full størrelser. Noen kameraer kan lagre både rå og jpeg-versjon.

Jeg har brukt en filstuktur organisert under år og fotoøkt. Dette er en vanlig metode, enkel for andre å finne frem i. Hver gang jeg laster ned et minnekort legger jeg inn bildene i filstrukturen før jeg sletter selve kortet. Dette for å unngå at duplikater blir hengende igjen. Jeg gjør det samme med bilder fra telefonen. Det betyr at bilder lagret på telefonen blir slettet. Med andre ord kan jeg ikke bruke telefonens galleri på vanlig måte for å se bilder jeg har tatt i fortiden.

Jeg har etterhvert hundretusen av bilder liggende på filstrukturen min. Det er nå over en terabyte med materiale. Det meste kan slettes, men det ville tatt veldig mye tid og tålmodighet uten noen stor forbedring.

En løsning er å arkivere originalfilene på eksterne media og eksportere dem til nedskalerte kopier. Lagringsbehovet reduseres da til en tiendedel eller mindre. Alle bildene kan dermed være tilgjengelige på arbeidsdisken uten å oppta mye plass. Originalene kan ligge på eksterne harddisker eller hvilket medium du skulle velge. De eksterne diskene kan dupliseres slik at backup kan legges et annet sted enn originalen. Til dette kan en bruke mindre eksterne harddisker eller f.eks blue-ray. Hvert fysiske medium merkes med et unikt navn. Backup merkes med det unike pluss informasjon om at det er en backup. Dette bør ligge som en JSON-fil på roten av mediet.

## Selve ideen

Kjernen i systemet er en database som inneholder all tilgjengelig informasjon om bildene og hvilket lagringsmedium originalbildene ligger på. Moderne bilder har EXIF-data som hentes ut automatisk og legges inn i databasen sammen med en thumbnail. Bilder fra f.eks scanner har ingen slik informasjon, men viktige ting som dato og sted kan legges inn manuelt.

Hovedideen er at en universell id er alt som behøves for å hente ut et bestemt bilde i ønsket versjon. I utgangspunktet lages nedskalerte versjoner automatisk. Nye versjoner kan legges inn, for eksempel etter editering i et fotoprogram. Bildets id kan legges inn i filnavnet når det hentes ut for redigering. Dermed kan spesielle versjoner registreres i databasen.

Et web-basert brukergrensesnitt kan være et fantastisk søkeverktøy i store bildesamlinger. Her kan du hente bilder basert på sted og dato for videre organisering og filtrering med ekstra informasjon du vil legge til. For eksempel kan du legge til tagger som lagres i databasen. Du kan også legge til info om bildet er "public" eller "private". Et annet eksempel er bildetekst. Nok et eksempel er rating. 

En viktig funksjon er gruppering av relaterte bilder. Databasen må ha informasjon som gjør det mulig for brukergrensesnittet å vise en gruppe av bilder som ett utalgt bilde. Grupperingen må gjøres manuelt av brukeren, eventuelt med støttefunksjon som å velge første og sist bilde i en serie. Grupper kan ha ulik funksjon, f.eks "serie", "motiv" eller "panorama". Særlig panorama kan være interessant for å hente data til programmer som PTGUI.

Med et fungerende webgrensesnitt vil det bli svært enkelt å sitte seine høstkvelder og gå gjennom materiale fra sommerens reiser. Fra de hundrevis eller tusenvis av bildene kan du først legge inn informasjon. Deretter kan du lage albumer. Jeg ser for meg å basere et album på Markdown. Dette kan brukes til alt fra lysbildeserier til fotobøker eller blogginnlegg. Markdown tar lite plass og kan legges inn i databasen.

## Programstruktur

Programmet bør bestå av kjerne og brukergrensesnitt som separate deler. Kjernen bør være api-basert.

### Kjernen
Kjernen har en database på bunnen. Den gjør det mulig med raske oppslag og enkel redigering av brukerdata. Større filer som bildefiler lagres i en filstruktur laget slik at det er enkelt å lagre store mengder små filer. Tilgang må være styrt av brukerrettigheter. En enkel strategi er å eksportere album og blogger til almennheten.

### Brukergrensesnittet
Det er overortnet viktig at brukergrensesnittet er enkelt og intuitivt å bruke. Startsiden skal være klar og tydelig med logisk plassering av  navigeringsverktøy.

Grunnleggende verktøy:
- Browser for bilder
- Viewer for bilder
- Editor for markdown, wysiwyg
- Robust og enkelt bibliotek for guikomponenter

Brukergrensesnittet bør være web-basert. Det bør ha redigeringsmodus og visningsmodus. Visningsmodus er åpen for alle, mens redigeringsmodus er privat.

## Overordnede krav til programkoden

Programmet må være veldokumentert og lett forståelig for nye programmerere. Kjerne og brukergrensesnitt må være separert. API må være strukturert slik at det passer som hånd i hanske med brukergrensesnittet uten å ha unødvendig funksjonalitet. Database og API må være lett å utvide uten å gjøre koden uoversiktlig.

Strategien er å bruke veldokumenterte verktøy og programbiblioteker på en mest mulig standardisert måte.

Det må være mulig å bruke ai til å holde oversikt over programstrukturen og kildefilene. Ideelt sett bør jeg kunne arbeide interaktivt sammen med ai for å komme fram til en programstruktur som fungerer, basert på enkle case. 

Det er en fordel at programmet utvikles i Python, men ved litt hjelp av ai kan jeg også prøve meg på javascript der et er hensiktsmessig.

## Innledende case

Min nåværende arbeidsflyt kan implementeres følgende steg:
1. Kopiere et minnekort til en katalog på disk og slette minnekortet. Dette må jeg gjøre manuelt
2. Gå gjennom filene på katalogen og lage underkataloger med navn "YYYY_MM_DD_tittel" som jeg kopierer filene til. Dette gjør jeg også manuelt
3. Starte brukergrensesnittet. Velge katalogen med bilder. Trykke på "Legg til" og få mulighet til å gi ekstra informasjon før informasjon legges til databasen.
4. Databasen har nå fått en opplasting som peker til en katalog med filer. Strukturen på katalogen er fri og bestemt av brukeren. Jeg vil kalle en slik katalog for "kilde". Den kan inneholde filen "innhold.json", som gir instruksjoner til kjernen
5. Databasen scanner kilde-katalogen for bildefiler. Hver fil registreres som et objekt i tabellen "filer". Merk at filer på rå-format kan ligge ved siden av en fil av typen jpeg for samme bilde. Dette må detekteres av programmet. Filen "innhold.json" kan gi instruksjoner om hvordan dette skal behandles. Det naturlige er å ha en tabell "bilder" med objekter som peker til et eller flere objekter i "filer".
6. For hver fil lages et element i tabellen "exif" dersom slike data finnes. Et utvalg verdier hentes fra filen og legges der for raskere tilgang.
7. For hvert bilde lages et element i "bilder" med referanse til en eller to filer (jpeg eller raw). Dersom mer enn ett velges et av dem som master ut fra en regel bestemt av brukeren. Enkleste regel vil være å bruke jpeg hvis den finnes og bruke raw ellers. Fra master genereres en liten thumbnail som legges i databasen for bildet. Fra thumbnail generes en hash som brukes til universelt oppslag. I tillegg lages en nedskalert versjon på ca 1000 piksler (medium) som legges i filsystemet. Denne filen gis navnet "<id>-<størrelse>.jpg", for eksempel "xxxx-medium.jpg". Sti til denne filen må kunne hentes via databasen.

Ved opplasting av ny kilde må følgende spseifiseres:
* Forfatter, obligatorisk: Den som har tatt alle bilder i kilden. Forfattere må ha egen tabell i databasen. 
* Notater: Eventuell beskrivelse av mediet kilden ligger på. Det kan typisk være en ekstern harddisk eller en katalog på et slikt medium.
* Strategi for å initialisere manglende exif-informasjon. For eksempel hente årstall og dato fra navn på foreldrekatalogen til bilde. Dette er nyttig for tidligere scannede bilder.

Det bør gis mulighet for å oppdatere "innhold.json" på kildemediet før opplasting. Det gjør det mulig å automatisk detektere en kilde i et tilkoblet medium. Mediet må selvsagt være skrivbart.