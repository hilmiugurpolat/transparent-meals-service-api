import json
import random
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

class RestaurantHTTPRequestHandler(BaseHTTPRequestHandler):
    def _set_headers(self, content_type='application/json'):
        self.send_response(200)
        self.send_header('Content-type', content_type)
        self.end_headers()

    def _load_data(self):
        with open('data.json', 'r') as file:
            return json.load(file)

    def _get_params(self):
        parsed_path = urlparse(self.path)
        return parse_qs(parsed_path.query)
    
    def _handle_get_request(self, endpoint, params):
        if endpoint == '/listMeals':
            self._list_meals(params)
        elif endpoint == '/getMeal':
            self._get_meal(params)
        elif endpoint == '/search':
            self._search_meal(params)
        else:
            self._set_error_headers(404)
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode('utf-8'))

    def _handle_post_request(self, endpoint, data):
        if endpoint == '/quality':
            self._calculate_quality(data)
        elif endpoint == '/price':
            self._calculate_price(data)
        elif endpoint == '/random':
            budget = float(data.get('budget', [float('inf')])[0])
            random_meal = self._get_random_meal(budget)
            self._set_headers()
            self.wfile.write(json.dumps(random_meal, indent=2).encode('utf-8'))
        elif endpoint == '/findHighest':
         self._find_highest_quality_meal(data)
        elif endpoint == '/findHighestOfMeal':
         self._find_highest_quality_of_meal(data)
        else:
            self._set_error_headers(404)
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode('utf-8'))

   
   
    def do_GET(self):
        params = self._get_params()
        endpoint = urlparse(self.path).path
        self._handle_get_request(endpoint, params)

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        post_params = parse_qs(post_data)
        endpoint = urlparse(self.path).path
        self._handle_post_request(endpoint, post_params)
    
    
    def _list_meals(self, params):
        data = self._load_data()
        is_vegetarian = params.get('is_vegetarian', ['false'])[0].lower() == 'true'
        is_vegan = params.get('is_vegan', ['false'])[0].lower() == 'true'

        filtered_menu = []
        for meal in data["meals"]:
            meal_id = meal.get("id")
            meal_name = meal.get("name")
            meal_ingredients = [ingredient.get("name") for ingredient in meal.get("ingredients", [])]

            if (is_vegetarian and all(ingredient in self._get_vegetarian_ingredients(data) for ingredient in meal_ingredients)) or \
               (is_vegan and all(ingredient in self._get_vegan_ingredients(data) for ingredient in meal_ingredients)):
                filtered_menu.append({"id": meal_id, "name": meal_name, "ingredients": meal_ingredients})
            elif not is_vegetarian and not is_vegan:
                filtered_menu.append({"id": meal_id, "name": meal_name, "ingredients": meal_ingredients})

        self._set_headers()
        self.wfile.write(json.dumps(filtered_menu, indent=2).encode('utf-8'))

    def _get_meal(self, params):
     meal_id = params.get('id', [None])[0]

     if meal_id is None:
        self._set_error_headers(400)
        self.wfile.write(json.dumps({"error": "Missing 'id' parameter"}).encode('utf-8'))
        return

     meal_id = int(meal_id)
     meal_data = next((meal for meal in self._load_data()["meals"] if meal["id"] == meal_id), None)

     if meal_data is None:
        self._set_error_headers(404)
        self.wfile.write(json.dumps({"error": "Meal not found"}).encode('utf-8'))
        return

     meal_name = meal_data["name"]
     meal_ingredients = []

     for ingredient_data in meal_data["ingredients"]:
        ingredient_name = ingredient_data["name"]
        ingredient_options = [opt for opt in self._load_data()["ingredients"] if opt["name"] == ingredient_name]

        ingredient_info = {
            "name": ingredient_name,
            "options": ingredient_options,
        }

        meal_ingredients.append(ingredient_info)

     meal_info = {
        "id": meal_id,
        "name": meal_name,
        "ingredients": meal_ingredients,
    }

     self._set_headers()
     self.wfile.write(json.dumps(meal_info, indent=2).encode('utf-8'))


    def _calculate_quality(self, data):
     meal_id = int(data.get('meal_id', [None])[0])
     if meal_id is None:
        self._set_error_headers(400)
        self.wfile.write(json.dumps({"error": "Missing 'meal_id' parameter"}).encode('utf-8'))
        return

     meal_data = next((meal for meal in self._load_data()["meals"] if meal["id"] == meal_id), None)
     if meal_data is None:
        self._set_error_headers(404)
        self.wfile.write(json.dumps({"error": "Meal not found"}).encode('utf-8'))
        return

     total_quality_score = 0

     for ingredient_data in meal_data["ingredients"]:
        ingredient_quality_str = data.get(ingredient_data["name"], ['high'])[0]

        if ingredient_quality_str == "low":
            ingredient_quality = 10
        elif ingredient_quality_str == "medium":
            ingredient_quality = 20
        elif ingredient_quality_str == "high":
            ingredient_quality = 30

        total_quality_score += ingredient_quality

     overall_quality = total_quality_score / len(meal_data["ingredients"])

     self._set_headers()
     self.wfile.write(json.dumps({"quality": overall_quality}).encode('utf-8'))
 

    def _calculate_price(self, data):
     meal_id = int(data.get('meal_id', [None])[0])
     if meal_id is None:
        self._set_error_headers(400)
        self.wfile.write(json.dumps({"error": "Missing 'meal_id' parameter"}).encode('utf-8'))
        return

     meal_data = next((meal for meal in self._load_data()["meals"] if meal["id"] == meal_id), None)
     if meal_data is None:
        self._set_error_headers(404)
        self.wfile.write(json.dumps({"error": "Meal not found"}).encode('utf-8'))
        return

     total_price = 0
     for ingredient_data in meal_data["ingredients"]:
        ingredient_quality_str = data.get(ingredient_data["name"], 'high')  # default quality is 'high' if not provided
        ingredient_options = ingredient_data.get("options", [])
        ingredient_price = 0

        if ingredient_options:
            for option in ingredient_options:
                if option["quality"] == ingredient_quality_str:
                    ingredient_price += option["price"]
                    break

        if ingredient_quality_str == "low":
            ingredient_price += 0.10  
        elif ingredient_quality_str == "medium":
            ingredient_price += 0.05  

        total_price += ingredient_price * (ingredient_data.get('quantity', 0) / 1000)  # Adjust price based on quantity

     self._set_headers()
     self.wfile.write(json.dumps({"price": round(total_price, 2)}).encode('utf-8'))

    def _get_random_meal(self, budget=None):
        data = self._load_data()
        random_meal = random.choice(data["meals"])
        
        meal_id = random_meal["id"]
        meal_name = random_meal["name"]
        meal_ingredients = []

        total_quality_score = 0
        total_price = 0

        for ingredient_data in random_meal["ingredients"]:
            ingredient_name = ingredient_data["name"]
            ingredient_quality = random.choice(["low", "medium", "high"])

            ingredient_options = ingredient_data.get("options", [])
            ingredient_price = 0

            if ingredient_options:
                for option in ingredient_options:
                    if option["quality"] == ingredient_quality:
                        ingredient_price += option["price"]
                        break

            total_price += ingredient_price

            ingredient_info = {
                "name": ingredient_name,
                "quality": ingredient_quality
            }

            meal_ingredients.append(ingredient_info)

        # If budget is specified, adjust the price accordingly
        if budget is not None:
            total_price = min(total_price, budget)

        overall_quality = total_quality_score // len(random_meal["ingredients"]) if meal_ingredients else 0
        overall_price = round(total_price, 2)

        meal_info = {
            "id": meal_id,
            "name": meal_name,
            "price": overall_price,
            "quality_score": overall_quality,
            "ingredients": meal_ingredients
        }

        return meal_info
    


    def _search_meal(self, params):
        query = params.get('query', [None])[0]

        if query is None:
            self._set_error_headers(400)
            self.wfile.write(json.dumps({"error": "Missing 'query' parameter"}).encode('utf-8'))
            return

        query = query.lower()
        matching_meals = []

        for meal in self._load_data()["meals"]:
            meal_id = meal.get("id")
            meal_name = meal.get("name")

            if query in meal_name.lower():
                meal_ingredients = [ingredient.get("name") for ingredient in meal.get("ingredients", [])]
                matching_meals.append({"id": meal_id, "name": meal_name, "ingredients": meal_ingredients})

        self._set_headers()
        self.wfile.write(json.dumps(matching_meals, indent=2).encode('utf-8'))
    
    
    
    def _find_highest_quality_meal(self, data):
     
     budget = float(data.get('budget', [0])[0])
     is_vegetarian = data.get('is_vegetarian', ['false'])[0].lower() == 'true'
     is_vegan = data.get('is_vegan', ['false'])[0].lower() == 'true'

     data = self._load_data()
     filtered_menu = []

     for meal in data["meals"]:
        meal_price = self._calculate_meal_price(meal)
        if meal_price <= budget:
            meal_quality = self._calculate_meal_quality(meal)
            if (is_vegetarian and all(ingredient in self._get_vegetarian_ingredients(data) for ingredient in meal.get("ingredients", []))) or \
               (is_vegan and all(ingredient in self._get_vegan_ingredients(data) for ingredient in meal.get("ingredients", []))) or \
               (not is_vegetarian and not is_vegan):
                filtered_menu.append((meal_quality, meal_price, meal))

     if filtered_menu:
        highest_quality_meal = max(filtered_menu, key=lambda x: x[0])
        meal_info = {
            "id": highest_quality_meal[2]["id"],
            "name": highest_quality_meal[2]["name"],
            "price": highest_quality_meal[1],
            "quality_score": highest_quality_meal[0],
            "ingredients": highest_quality_meal[2].get("ingredients", [])
        }
        self._set_headers()
        self.wfile.write(json.dumps(meal_info, indent=2).encode('utf-8'))
     else:
        self._set_error_headers(404)
        self.wfile.write(json.dumps({"error": "No meal found within the specified budget and dietary restrictions"}).encode('utf-8'))


    def _calculate_meal_price(self, meal):
     total_price = 0
     for ingredient_data in meal["ingredients"]:
        ingredient_name = ingredient_data["name"]
        ingredient_options = ingredient_data.get("options", [])
        ingredient_price = 0

        if ingredient_options:
            for option in ingredient_options:
                ingredient_price += option["price"]

        total_price += ingredient_price

     return total_price

    def _calculate_meal_quality(self, meal):
     total_quality_score = 0
     for ingredient_data in meal["ingredients"]:
        ingredient_quality = 0
        ingredient_options = ingredient_data.get("options", [])
        if ingredient_options:
            for option in ingredient_options:
                ingredient_quality += self._get_option_quality(option)

        total_quality_score += ingredient_quality

     return total_quality_score / len(meal["ingredients"]) if meal["ingredients"] else 0


    def _find_highest_quality_of_meal(self, data):
     meal_id = int(data.get('meal_id', [0])[0])
     budget = float(data.get('budget', [0])[0])

     data = self._load_data()
     meal = self._find_meal_by_id(data, meal_id)

     if meal:
        meal_price = self._calculate_meal_price(meal)
        if meal_price <= budget:
            meal_quality = self._calculate_meal_quality(meal)
            meal_info = {
                "id": meal["id"],
                "name": meal["name"],
                "price": meal_price,
                "quality_score": meal_quality,
                "ingredients": meal.get("ingredients", [])
            }
            self._set_headers()
            self.wfile.write(json.dumps(meal_info, indent=2).encode('utf-8'))
        else:
            self._set_error_headers(404)
            self.wfile.write(json.dumps({"error": "The specified budget is not enough to afford the meal"}).encode('utf-8'))
     else:
        self._set_error_headers(404)
        self.wfile.write(json.dumps({"error": "Meal not found with the specified ID"}).encode('utf-8'))


    def _find_meal_by_id(self, data, meal_id):
     for meal in data['meals']:
        if meal['id'] == meal_id:
            return meal
     return None



    def _get_vegetarian_ingredients(self, data):
        return [ingredient["name"] for ingredient in data["ingredients"] if "vegetarian" in ingredient.get("groups", [])]

    def _get_vegan_ingredients(self, data):
        return [ingredient["name"] for ingredient in data["ingredients"] if "vegan" in ingredient.get("groups", [])]

    def _get_option_quality(self, option):
        if option["quality"] == "low":
            return 10
        elif option["quality"] == "medium":
            return 20
        elif option["quality"] == "high":
            return 30

    def _set_error_headers(self, status_code):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode('utf-8'))

    

def run(server_class=HTTPServer, handler_class=RestaurantHTTPRequestHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting server on port {port}")
    httpd.serve_forever()

if __name__ == "__main__":
    run()
