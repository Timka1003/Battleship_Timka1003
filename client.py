import tkinter as tk
from tkinter import messagebox, font
import string
import requests
import time
from threading import Thread, Event
from math import sin, cos, radians

SERVER_URL = "http://127.0.0.1:5000"
GRID_SIZE = 10
CELL_SIZE = 50
SHIP_TYPES = {
    "ship1": 1,
    "ship2": 1,
    "ship3": 1,
    "ship4": 1,
    "ship5": 1
}

# Цветовая схема
OCEAN_COLOR = "#006994"
GRID_COLOR = "#88aaff"
WAVE_COLOR = "#aaddff"
SHIP_COLORS = {
    "ship1": "#4a6741",
    "ship2": "#5b5d4e",
    "ship3": "#6b8e23",
    "ship4": "#4b5320",
    "ship5": "#3a5f0b"
}
HIT_COLOR = "#ff3333"
MISS_COLOR = "#add8e6"
TEXT_COLOR = "#ffffff"
BG_COLOR = "#1e1e2e"
BTN_COLOR = "#3b3b4f"

class BattleshipApp:
    def __init__(self, master):
        self.master = master
        self.setup_window()
        self.init_game_state()
        self.init_ships()
        self.setup_widgets()
        self.create_menu()
        self.start_polling_thread()

    def setup_window(self):
        self.master.title("Морской Бой - 5 кораблей")
        self.master.geometry("1100x800")
        self.master.resizable(False, False)
        self.master.configure(bg=BG_COLOR)
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)

    def init_game_state(self):
        self.player = None
        self.ships = []
        self.hits_on_me = []
        self.misses_on_me = []
        self.my_hits = []
        self.my_misses = []
        self.turn = None
        self.game_over = False
        self.placing_ships = True
        self.opponent_ready = False
        self.running = True
        self.poll_event = Event()
        self.selected_ship = None
        self.ship_orientation = "horizontal"
        self.dragging = False
        self.drag_start_pos = None

    def init_ships(self):
        self.ships = []
        for ship_type, size in SHIP_TYPES.items():
            self.ships.append({
                "type": ship_type,
                "size": size,
                "coords": [],
                "hits": []
            })
        self.selected_ship = None

    def setup_widgets(self):
        self.status_label = tk.Label(
            self.master, text="", font=("Arial", 14), 
            fg=TEXT_COLOR, bg=BG_COLOR
        )
        self.ship_count_label = tk.Label(
            self.master, text="", font=("Arial", 12), 
            fg=TEXT_COLOR, bg=BG_COLOR
        )
        self.my_canvas = None
        self.enemy_canvas = None
        self.start_button = None
        self.rotate_button = None

    def create_menu(self):
        self.clear_screen()
        self.status_label.pack(pady=10)

        tk.Label(
            self.master, text="Морской Бой", 
            font=("Arial", 24, "bold"), 
            fg=TEXT_COLOR, bg=BG_COLOR
        ).pack(pady=20)

        tk.Label(
            self.master, text="Выберите игрока:", 
            font=("Arial", 14), 
            fg=TEXT_COLOR, bg=BG_COLOR
        ).pack(pady=10)

        btn_frame = tk.Frame(self.master, bg=BG_COLOR)
        btn_frame.pack(pady=10)

        tk.Button(
            btn_frame, text="Player 1", 
            command=lambda: self.set_player("player1"), 
            width=15, height=2, bg=BTN_COLOR,
            fg=TEXT_COLOR, font=("Arial", 12)
        ).grid(row=0, column=0, padx=10)

        tk.Button(
            btn_frame, text="Player 2", 
            command=lambda: self.set_player("player2"), 
            width=15, height=2, bg=BTN_COLOR,
            fg=TEXT_COLOR, font=("Arial", 12)
        ).grid(row=0, column=1, padx=10)

    def set_player(self, player):
        self.player = player
        self.ask_restart()

    def ask_restart(self):
        if messagebox.askyesno("Рестарт", "Начать новую игру?"):
            try:
                response = requests.post(f"{SERVER_URL}/restart", timeout=3)
                if response.status_code == 200:
                    requests.post(
                        f"{SERVER_URL}/reset_ready", 
                        json={"player": self.player},
                        timeout=3
                    )
            except requests.exceptions.RequestException:
                messagebox.showerror("Ошибка", "Не удалось подключиться к серверу.")
                return
        self.draw_fields()

    def draw_fields(self):
        self.clear_screen()
        self.init_ships()
        self.status_label.pack(pady=10)

        board_frame = tk.Frame(self.master, bg=BG_COLOR)
        board_frame.pack(pady=20)

        self.create_player_board(board_frame)
        self.create_enemy_board(board_frame)

        self.ship_count_label.pack()
        self.create_control_buttons()
        self.draw_grids()
        self.update_status()

    def create_player_board(self, parent):
        player_frame = tk.Frame(parent, bg=BG_COLOR)
        player_frame.grid(row=0, column=0, padx=20)

        tk.Label(
            player_frame, text="Ваши корабли", 
            font=("Arial", 14, "bold"), 
            fg=TEXT_COLOR, bg=BG_COLOR
        ).pack()

        self.my_canvas = tk.Canvas(
            player_frame, width=CELL_SIZE*GRID_SIZE, 
            height=CELL_SIZE*GRID_SIZE, bg=OCEAN_COLOR,
            highlightthickness=0
        )
        self.my_canvas.pack(pady=10)
        self.my_canvas.bind("<Button-1>", self.on_my_canvas_click)

    def create_enemy_board(self, parent):
        enemy_frame = tk.Frame(parent, bg=BG_COLOR)
        enemy_frame.grid(row=0, column=1, padx=20)

        tk.Label(
            enemy_frame, text="Противник", 
            font=("Arial", 14, "bold"), 
            fg=TEXT_COLOR, bg=BG_COLOR
        ).pack()

        self.enemy_canvas = tk.Canvas(
            enemy_frame, width=CELL_SIZE*GRID_SIZE, 
            height=CELL_SIZE*GRID_SIZE, bg=OCEAN_COLOR,
            highlightthickness=0
        )
        self.enemy_canvas.pack(pady=10)
        self.enemy_canvas.bind("<Button-1>", self.on_enemy_canvas_click)

    def create_control_buttons(self):
        btn_frame = tk.Frame(self.master, bg=BG_COLOR)
        btn_frame.pack(pady=10)

        if self.placing_ships:
            self.start_button = tk.Button(
                btn_frame, text="Готово", 
                command=self.start_battle, width=15,
                height=1, bg="#4CAF50", fg=TEXT_COLOR,
                font=("Arial", 10), state=tk.DISABLED
            )
            self.start_button.pack()

    def draw_ship(self, canvas, ship):
        ship_type = ship["type"]
        coord = ship["coords"][0] if ship["coords"] else None
        
        if coord:
            row = string.ascii_uppercase.index(coord[0])
            col = int(coord[1:]) - 1
            
            x1 = col * CELL_SIZE
            y1 = row * CELL_SIZE
            x2 = x1 + CELL_SIZE
            y2 = y1 + CELL_SIZE
            
            fill_color = SHIP_COLORS.get(ship_type, "#4a6741")
            if coord in ship.get("hits", []):
                fill_color = HIT_COLOR
                
            canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=fill_color, outline="#1e3f1a",
                width=2, tags="ship"
            )

    def draw_grids(self):
        if not self.my_canvas or not self.enemy_canvas:
            return
            
        self.my_canvas.delete("all")
        self.enemy_canvas.delete("all")
        
        # Рисуем сетку
        for i in range(GRID_SIZE+1):
            self.my_canvas.create_line(
                0, i*CELL_SIZE, GRID_SIZE*CELL_SIZE, i*CELL_SIZE,
                fill=GRID_COLOR, width=1
            )
            self.my_canvas.create_line(
                i*CELL_SIZE, 0, i*CELL_SIZE, GRID_SIZE*CELL_SIZE,
                fill=GRID_COLOR, width=1
            )
            self.enemy_canvas.create_line(
                0, i*CELL_SIZE, GRID_SIZE*CELL_SIZE, i*CELL_SIZE,
                fill=GRID_COLOR, width=1
            )
            self.enemy_canvas.create_line(
                i*CELL_SIZE, 0, i*CELL_SIZE, GRID_SIZE*CELL_SIZE,
                fill=GRID_COLOR, width=1
            )
        
        # Рисуем корабли
        for ship in self.ships:
            self.draw_ship(self.my_canvas, ship)
        
        # Рисуем выстрелы
        self.draw_shots(self.my_canvas, is_player=True)
        self.draw_shots(self.enemy_canvas, is_player=False)
        
        # Подписи координат
        self.add_coordinate_labels()

    def draw_shots(self, canvas, is_player):
        shots = self.hits_on_me + self.misses_on_me if is_player else self.my_hits + self.my_misses
        hits = self.hits_on_me if is_player else self.my_hits
        
        for coord in shots:
            row = string.ascii_uppercase.index(coord[0])
            col = int(coord[1:]) - 1
            x1 = col * CELL_SIZE + 5
            y1 = row * CELL_SIZE + 5
            x2 = (col+1) * CELL_SIZE - 5
            y2 = (row+1) * CELL_SIZE - 5
            
            if coord in hits:
                canvas.create_oval(
                    x1, y1, x2, y2,
                    fill=HIT_COLOR, outline="orange", width=2
                )
            else:
                canvas.create_oval(x1, y1, x2, y2, outline=MISS_COLOR, width=2)

    def add_coordinate_labels(self):
        for i in range(GRID_SIZE):
            self.my_canvas.create_text(
                5, i * CELL_SIZE + CELL_SIZE // 2,
                text=string.ascii_uppercase[i], anchor="w", fill="white"
            )
            self.enemy_canvas.create_text(
                5, i * CELL_SIZE + CELL_SIZE // 2,
                text=string.ascii_uppercase[i], anchor="w", fill="white"
            )
            self.my_canvas.create_text(
                i * CELL_SIZE + CELL_SIZE // 2, 5,
                text=str(i+1), anchor="n", fill="white"
            )
            self.enemy_canvas.create_text(
                i * CELL_SIZE + CELL_SIZE // 2, 5,
                text=str(i+1), anchor="n", fill="white"
            )

    def on_my_canvas_click(self, event):
        if not self.placing_ships:
            return
            
        col = event.x // CELL_SIZE
        row = event.y // CELL_SIZE
        
        if 0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE:
            coord = f"{string.ascii_uppercase[row]}{col+1}"
            self.place_ship(coord)

    def place_ship(self, coord):
        # Находим первый корабль без координат
        for ship in self.ships:
            if not ship["coords"]:
                # Проверяем, что клетка свободна
                for other_ship in self.ships:
                    if coord in other_ship["coords"]:
                        messagebox.showwarning("Ошибка", "Клетка уже занята!")
                        return
                
                ship["coords"] = [coord]
                self.draw_grids()
                self.check_ships_placed()
                return
        
        messagebox.showinfo("Информация", "Все корабли уже размещены")

    def on_enemy_canvas_click(self, event):
        if self.placing_ships or self.game_over or self.turn != self.player:
            return
            
        col = event.x // CELL_SIZE
        row = event.y // CELL_SIZE
        
        if 0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE:
            coord = f"{string.ascii_uppercase[row]}{col+1}"
            self.fire_shot(coord)

    def fire_shot(self, coord):
        try:
            response = requests.post(
                f"{SERVER_URL}/fire",
                json={"player": self.player, "target": coord},
                timeout=3
            ).json()
            
            if "error" in response:
                messagebox.showerror("Ошибка", response["error"])
            else:
                if response.get("game_over"):
                    self.game_over = True
                    winner = response.get("winner")
                    if winner == self.player:
                        messagebox.showinfo("Победа!", "Вы выиграли!")
                    else:
                        messagebox.showinfo("Поражение", "Вы проиграли.")
        except requests.exceptions.RequestException:
            messagebox.showerror("Ошибка", "Не удалось отправить выстрел.")
        
        self.update_status()

    def start_battle(self):
        placed_ships = [ship for ship in self.ships if ship["coords"]]
        if len(placed_ships) != 5:
            messagebox.showwarning("Ошибка", "Разместите ровно 5 кораблей!")
            return
            
        try:
            ship_coords = []
            for ship in self.ships:
                ship_coords.extend(ship["coords"])
                
            response = requests.post(
                f"{SERVER_URL}/place_ships",
                json={"player": self.player, "ships": ship_coords},
                timeout=3
            ).json()
            
            if "error" in response:
                messagebox.showerror("Ошибка", response["error"])
            else:
                self.placing_ships = False
                if self.start_button:
                    self.start_button.destroy()
                messagebox.showinfo("Успех", "Корабли размещены! Ожидайте начала игры.")
                
        except requests.exceptions.RequestException:
            messagebox.showerror("Ошибка", "Не удалось отправить корабли на сервер")

    def check_ships_placed(self):
        placed_ships = [ship for ship in self.ships if ship["coords"]]
        if self.start_button:
            self.start_button.config(state=tk.NORMAL if len(placed_ships) == 5 else tk.DISABLED)
            self.status_label.config(text=f"Размещено кораблей: {len(placed_ships)}/5")

    def update_status(self):
        try:
            response = requests.get(f"{SERVER_URL}/status", timeout=3).json()
            
            self.turn = response.get("current_turn", self.player)
            self.game_over = response.get("game_over", False)
            
            self.hits_on_me = response.get(f"{self.player}_hits", [])
            self.misses_on_me = response.get(f"{self.player}_misses", [])
            
            opponent = "player2" if self.player == "player1" else "player1"
            self.my_hits = response.get(f"{opponent}_hits", [])
            self.my_misses = response.get(f"{opponent}_misses", [])
            
            self.opponent_ready = response.get(
                "player2_ready" if self.player == "player1" else "player1_ready", 
                False
            )
            
            status_text = self.get_status_text(response)
            self.status_label.config(text=status_text)
            
            self.draw_grids()
            
        except requests.exceptions.RequestException:
            self.status_label.config(text="Ошибка соединения с сервером")

    def get_status_text(self, response):
        if self.game_over:
            winner = response.get("winner")
            return "Вы выиграли!" if winner == self.player else "Вы проиграли."
        elif self.placing_ships:
            placed = len([ship for ship in self.ships if ship["coords"]])
            return f"Размещено кораблей: {placed}/5"
        else:
            return "Ваш ход!" if self.turn == self.player else "Ход противника..."

    def start_polling_thread(self):
        self.poll_thread = Thread(target=self.poll_game_status)
        self.poll_thread.daemon = True
        self.poll_thread.start()

    def poll_game_status(self):
        while self.running:
            try:
                time.sleep(1)
                if not self.running:
                    break
                    
                self.master.after(0, self.update_status)
            except:
                continue

    def clear_screen(self):
        for widget in self.master.winfo_children():
            widget.destroy()
        self.setup_widgets()

    def on_close(self):
        self.running = False
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = BattleshipApp(root)
    root.mainloop()