# websocket client
That tools is a rudimentary development for reading data through a websocket.

# How to use websocket script ?
In first time, it's necessary to install websockets by using pip with the following command line :

<!--sec data-title="Prompt: macOS and Linux" data-id="OSX_Linux_prompt" data-collapse=true ces-->
    pip install websockets
<!--endsec-->

After that, you can use script by using :

<!--sec data-title="Prompt: macOS and Linux" data-id="OSX_Linux_prompt" data-collapse=true ces-->
    python websocket.py
<!--endsec-->

Finally, inform IP address following by WebSocket port of the equippement and then <b>ENTER</b> :
<!--sec data-title="Prompt: macOS and Linux" data-id="OSX_Linux_prompt" data-collapse=true ces-->
    Entrez l'adresse IP ou le hostname du serveur WebSocket (ex: 192.168.1.10:8765):
<!--endsec-->

In the [Module TIC](https://github.com/bastoon577-lang/Module-TIC-SOFTWARE) context, you could see following data on terminal :
<!--sec data-title="Prompt: macOS and Linux" data-id="OSX_Linux_prompt" data-collapse=true ces-->
    Tentative de connexion à ws://192.168.43.113:81 ...                                
    Connecté au serveur WebSocket.                                                      
    En attente de messages...
    Message reçu : {"HHPHC":"A"}                                                        
    Message reçu : {"BASE":"002844816"}                                                 
    Message reçu : {"ADCO":"022064215196"}                                             
    Message reçu : {"HCHC":"034366502"}                                                
    Message reçu : {"ISOUSC":"30"}                                                     
    Message reçu : {"PTEC":"HP.."}
<!--endsec-->

###### Auteur : *Sébastien DALIGAULT*. 
