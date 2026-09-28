import csv
import json
import threading
import asyncio
import socket
from datetime import datetime
from urllib.parse import urlparse
import websockets
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

class AppTIC(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Lecteur WebSocket TIC v1.0")
        self.geometry("750x620")

        # État centralisé des dernières valeurs reçues {Etiquette: Valeur}
        self.raw_data = {}  
        
        # État d'enregistrement
        self.is_recording = False
        self.time_series_records = []  
        self.recorded_labels = set()  # Capture dynamique de toutes les étiquettes vues

        self.websocket_loop = None
        self.is_connected = False

        self._build_ui()

    def _build_ui(self):
        # --- Frame Connexion ---
        frame_conn = ttk.LabelFrame(self, text=" Connexion WebSocket ")
        frame_conn.pack(fill="x", padx=10, pady=5)

        ttk.Label(frame_conn, text="IP / Hostname :").pack(side="left", padx=5, pady=5)
        self.entry_host = ttk.Entry(frame_conn, width=30)
        self.entry_host.insert(0, "ModuleTIC.local:443")
        self.entry_host.pack(side="left", padx=5, pady=5)

        self.btn_lire = ttk.Button(frame_conn, text="Lire", command=self.toggle_connection)
        self.btn_lire.pack(side="left", padx=5, pady=5)

        self.lbl_dns_info = ttk.Label(self, text="Statut : Non connecté", font=("TkDefaultFont", 8, "italic"))
        self.lbl_dns_info.pack(fill="x", padx=15, pady=(0, 5))

        # --- Frame Filtres ---
        frame_filter = ttk.LabelFrame(self, text=" Filtres d'affichage (séparés par des virgules) ")
        frame_filter.pack(fill="x", padx=10, pady=5)

        ttk.Label(frame_filter, text="Étiquettes :").pack(side="left", padx=5, pady=5)
        self.entry_filter = ttk.Entry(frame_filter)
        # Utilisation d'un placeholder explicatif sans imposer de valeur par défaut
        self.entry_filter.insert(0, "")
        self.entry_filter.config(foreground="black")
        self.entry_filter.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        self.entry_filter.bind("<KeyRelease>", lambda e: self.update_table())

        # Indication visuelle d'exemple
        lbl_hint = ttk.Label(frame_filter, text="(Ex: IINST, PAPP)", font=("TkDefaultFont", 8, "italic"), foreground="gray")
        lbl_hint.pack(side="right", padx=5)

        # --- Tableau des données ---
        frame_table = ttk.Frame(self)
        frame_table.pack(fill="both", expand=True, padx=10, pady=5)

        self.table = ttk.Treeview(frame_table, columns=("Etiquette", "Valeur"), show="headings")
        self.table.heading("Etiquette", text="Étiquette")
        self.table.heading("Valeur", text="Valeur")
        self.table.column("Etiquette", width=220, anchor="w")
        self.table.column("Valeur", width=430, anchor="w")

        scrollbar = ttk.Scrollbar(frame_table, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)

        self.table.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # --- Frame Actions ---
        frame_actions = ttk.Frame(self)
        frame_actions.pack(fill="x", padx=10, pady=10)

        self.lbl_record_status = ttk.Label(frame_actions, text="● Enregistrement inactif", foreground="gray")
        self.lbl_record_status.pack(side="left", padx=5)

        self.btn_save = ttk.Button(frame_actions, text="Démarrer enregistrement", command=self.toggle_recording)
        self.btn_save.pack(side="right", padx=5)

        self.btn_quit = ttk.Button(frame_actions, text="Quitter", command=self.on_closing)
        self.btn_quit.pack(side="right", padx=5)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def get_filter_list(self):
        """Découpe la chaîne de filtres si renseignée."""
        raw_filter = self.entry_filter.get().strip()
        if not raw_filter:
            return []
        return [f.strip().upper() for f in raw_filter.split(",") if f.strip()]

    def is_matching_filter(self, key: str) -> bool:
        """Filtre uniquement l'affichage de l'interface graphique."""
        filters = self.get_filter_list()
        if not filters:
            return True
        k_upper = key.upper()
        return any(f in k_upper for f in filters)

    def prepare_uri(self, input_host: str):
        raw = input_host.strip()
        if not raw.startswith(("ws://", "wss://")):
            url_to_parse = f"ws://{raw}"
        else:
            url_to_parse = raw

        parsed = urlparse(url_to_parse)
        hostname = parsed.hostname or raw.split(":")[0].replace("ws://", "").replace("wss://", "")
        port = parsed.port if parsed.port else 443
        scheme = parsed.scheme if parsed.scheme else "ws"

        resolved_ip = "Non résolu"
        try:
            resolved_ip = socket.gethostbyname(hostname)
        except Exception:
            pass

        return f"{scheme}://{hostname}:{port}", hostname, resolved_ip

    def parse_message(self, message: str):
        """Mise à jour en continu du dictionnaire d'état au fur et à mesure de l'arrivée des trames."""
        try:
            data = json.loads(message)
            if isinstance(data, dict):
                for k, v in data.items():
                    key_up = str(k).upper()
                    self.raw_data[key_up] = str(v)
                    if self.is_recording:
                        self.recorded_labels.add(key_up)
        except json.JSONDecodeError:
            parts = message.strip().split()
            if len(parts) >= 2:
                key_up = parts[0].upper()
                val = " ".join(parts[1:])
                self.raw_data[key_up] = val
                if self.is_recording:
                    self.recorded_labels.add(key_up)
            else:
                key_up = message.upper()
                self.raw_data[key_up] = ""
                if self.is_recording:
                    self.recorded_labels.add(key_up)

    def record_tick(self):
        """Prend un instantané régulier toutes les 1000 ms."""
        if not self.is_recording:
            return

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # On enregistre l'état stabilisé de toutes les étiquettes connues à cet instant
        snapshot_row = {"Date": now_str}
        snapshot_row.update(self.raw_data)

        self.time_series_records.append(snapshot_row)

        # Programmation du prochain relevé à 1 seconde
        self.after(1000, self.record_tick)

    def update_table(self):
        """Mise à jour du tableau visuel."""
        for item in self.table.get_children():
            self.table.delete(item)

        for key, val in sorted(self.raw_data.items()):
            if self.is_matching_filter(key):
                self.table.insert("", "end", values=(key, val))

    def toggle_connection(self):
        if not self.is_connected:
            raw_input = self.entry_host.get().strip()
            if not raw_input:
                messagebox.showerror("Erreur", "Veuillez entrer une adresse valide.")
                return

            uri, hostname, resolved_ip = self.prepare_uri(raw_input)
            self.lbl_dns_info.config(
                text=f"Connexion à {uri} (IP: {resolved_ip})...", 
                foreground="orange"
            )

            self.is_connected = True
            self.btn_lire.config(text="S'arrêter")

            threading.Thread(target=self._run_asyncio_loop, args=(uri,), daemon=True).start()
        else:
            self.is_connected = False
            self.btn_lire.config(text="Lire")
            self.lbl_dns_info.config(text="Statut : Déconnecté", foreground="black")

    def _run_asyncio_loop(self, uri):
        self.websocket_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.websocket_loop)
        self.websocket_loop.run_until_complete(self._listen_websocket(uri))

    async def _listen_websocket(self, uri):
        try:
            async with websockets.connect(uri, ping_interval=None) as websocket:
                self.after(0, lambda: self.lbl_dns_info.config(
                    text=f"Connecté avec succès à {uri}", foreground="green"
                ))
                while self.is_connected:
                    message = await websocket.recv()
                    self.parse_message(message)
                    self.after(0, self.update_table)
        except Exception as e:
            if self.is_connected:
                self.after(0, lambda err=e: messagebox.showerror("Erreur de connexion", f"{err}"))
                self.after(0, lambda err=e: self.lbl_dns_info.config(
                    text=f"Erreur : {err}", foreground="red"
                ))
        finally:
            self.is_connected = False
            self.after(0, lambda: self.btn_lire.config(text="Lire"))

    def toggle_recording(self):
        if not self.is_recording:
            self.time_series_records.clear()
            self.recorded_labels.clear()
            
            # Initialisation avec les clés déjà présentes au démarrage de l'enregistrement
            for k in self.raw_data.keys():
                self.recorded_labels.add(k)

            self.is_recording = True
            self.btn_save.config(text="Arrêter l'enregistrement")
            self.lbl_record_status.config(text="● Enregistrement en cours...", foreground="red")

            # Lancement de la boucle temporelle d'enregistrement
            self.record_tick()
        else:
            self.is_recording = False
            self.btn_save.config(text="Démarrer enregistrement")
            self.lbl_record_status.config(text="● Enregistrement inactif", foreground="gray")
            self.export_time_series_csv()

    def export_time_series_csv(self):
        if not self.time_series_records:
            messagebox.showwarning("Attention", "Aucune donnée enregistrée.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")],
            title="Enregistrer la série temporelle TIC"
        )

        if filepath:
            try:
                # Filtrage optionnel : si un filtre est actif dans la zone de texte, on n'exporte que ces colonnes
                active_filters = self.get_filter_list()
                if active_filters:
                    selected_labels = [lbl for lbl in sorted(list(self.recorded_labels)) if any(f in lbl for f in active_filters)]
                else:
                    selected_labels = sorted(list(self.recorded_labels))

                headers = ["Date"] + selected_labels
                
                with open(filepath, mode="w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=headers, delimiter=";", extrasaction="ignore")
                    writer.writeheader()
                    for row in self.time_series_records:
                        writer.writerow(row)

                messagebox.showinfo("Succès", f"Fichier sauvegardé ({len(self.time_series_records)} lignes enregistrées à 1s d'intervalle).")
            except Exception as e:
                messagebox.showerror("Erreur d'écriture", str(e))

    def on_closing(self):
        self.is_connected = False
        self.is_recording = False
        if self.websocket_loop and self.websocket_loop.is_running():
            self.websocket_loop.stop()
        self.destroy()

if __name__ == "__main__":
    app = AppTIC()
    app.mainloop()