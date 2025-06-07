from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Разрешаем кросс-доменные запросы

# Инициализация игры
players = {
    "player1": {"ships": [], "hits": [], "misses": [], "ready": False},
    "player2": {"ships": [], "hits": [], "misses": [], "ready": False}
}
current_turn = "player1"
game_over = False
winner = None

def init_game():
    global players, current_turn, game_over, winner
    players = {
        "player1": {"ships": [], "hits": [], "misses": [], "ready": False},
        "player2": {"ships": [], "hits": [], "misses": [], "ready": False}
    }
    current_turn = "player1"
    game_over = False
    winner = None

@app.route("/place_ships", methods=["POST"])
def place_ships():
    global current_turn, game_over
    
    data = request.json
    player = data.get("player")
    ships = data.get("ships", [])
    
    if player not in players:
        return jsonify({"error": "Неверный игрок"}), 400
    
    # Проверка количества кораблей
    if len(ships) != 5:
        return jsonify({"error": "Должно быть ровно 5 кораблей"}), 400
    
    # Проверка валидности координат
    valid_coords = [f"{l}{n}" for l in "ABCDEFGHIJ" for n in range(1, 11)]
    for coord in ships:
        if coord not in valid_coords:
            return jsonify({"error": f"Неверная координата: {coord}"}), 400
    
    players[player]["ships"] = ships
    players[player]["ready"] = True
    
    # Проверяем, готовы ли оба игрока
    if players["player1"]["ready"] and players["player2"]["ready"]:
        current_turn = "player1"  # Первым ходит player1
    
    return jsonify({
        "status": "Корабли расставлены!",
        "ready": players[player]["ready"],
        "both_ready": players["player1"]["ready"] and players["player2"]["ready"]
    })

@app.route("/fire", methods=["POST"])
def fire():
    global current_turn, game_over, winner
    
    if game_over:
        return jsonify({"result": "Игра окончена!", "winner": winner})
    
    data = request.json
    player = data.get("player")
    target = data.get("target")
    
    if player not in players:
        return jsonify({"error": "Неверный игрок"}), 400
    
    if player != current_turn:
        return jsonify({"error": "Сейчас не ваш ход!"}), 400
    
    opponent = "player2" if player == "player1" else "player1"
    
    # Проверка валидности координаты
    valid_coords = [f"{l}{n}" for l in "ABCDEFGHIJ" for n in range(1, 11)]
    if target not in valid_coords:
        return jsonify({"error": "Неверная координата"}), 400
    
    if target in players[opponent]["hits"] or target in players[opponent]["misses"]:
        return jsonify({"result": "Уже стреляли сюда!"})
    
    result = ""
    if target in players[opponent]["ships"]:
        players[opponent]["hits"].append(target)
        result = "Попал!"
        
        # Проверяем, остались ли корабли у противника
        remaining = set(players[opponent]["ships"]) - set(players[opponent]["hits"])
        if not remaining:
            result = "Все корабли противника уничтожены. Победа!"
            game_over = True
            winner = player
    else:
        players[opponent]["misses"].append(target)
        result = "Мимо!"
        current_turn = opponent
    
    return jsonify({
        "result": result,
        "turn": current_turn,
        "game_over": game_over,
        "winner": winner
    })

@app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "current_turn": current_turn,
        "game_over": game_over,
        "winner": winner,
        "player1_ready": players["player1"]["ready"],
        "player2_ready": players["player2"]["ready"],
        "player1_hits": players["player1"]["hits"],
        "player1_misses": players["player1"]["misses"],
        "player2_hits": players["player2"]["hits"],
        "player2_misses": players["player2"]["misses"]
    })

@app.route("/restart", methods=["POST"])
def restart():
    init_game()
    return jsonify({"status": "Игра перезапущена!"})

@app.route("/reset_ready", methods=["POST"])
def reset_ready():
    player = request.json.get("player")
    if player in players:
        players[player]["ready"] = False
    return jsonify({"status": "Готовность сброшена"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)