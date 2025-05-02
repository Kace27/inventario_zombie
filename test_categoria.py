import os
import sqlite3
import json
import requests
import time
import sys

def test_categoria_api():
    """Test if the categoria field works correctly through the API"""
    print("Testing categoria field functionality...")
    
    base_url = "http://127.0.0.1:5000/api"
    
    # 1. Create a new ingredient with categoria
    print("\n1. Creating new ingredient with categoria...")
    new_ingredient = {
        "nombre": f"Test Ingredient {int(time.time())}",
        "unidad_medida": "kg",
        "precio_compra": 25.5,
        "cantidad_actual": 15,
        "stock_minimo": 5,
        "categoria": "Vegetales"
    }
    
    try:
        response = requests.post(f"{base_url}/ingredientes", json=new_ingredient)
        response.raise_for_status()
        created_ingredient = response.json()
        print(f"API Response: {json.dumps(created_ingredient, indent=2)}")
        
        ingredient_id = created_ingredient.get('id')
        
        if ingredient_id:
            print(f"Successfully created ingredient with ID: {ingredient_id}")
            
            # Check if categoria was saved properly
            if created_ingredient.get('categoria') == "Vegetales":
                print("✅ Categoria field was saved correctly")
            else:
                print(f"❌ Categoria field was not saved correctly. Value: {created_ingredient.get('categoria')}")
            
            # 2. Update the ingredient's categoria
            print("\n2. Updating ingredient categoria...")
            updated_data = {
                "categoria": "Frutas"
            }
            
            response = requests.put(f"{base_url}/ingredientes/{ingredient_id}", json=updated_data)
            response.raise_for_status()
            updated_ingredient = response.json()
            print(f"API Response: {json.dumps(updated_ingredient, indent=2)}")
            
            # Check if categoria was updated properly
            if updated_ingredient.get('categoria') == "Frutas":
                print("✅ Categoria field was updated correctly")
            else:
                print(f"❌ Categoria field was not updated correctly. Value: {updated_ingredient.get('categoria')}")
            
            # 3. Get the ingredient and check categoria
            print("\n3. Getting ingredient to verify categoria...")
            response = requests.get(f"{base_url}/ingredientes/{ingredient_id}")
            response.raise_for_status()
            fetched_ingredient = response.json()
            print(f"API Response: {json.dumps(fetched_ingredient, indent=2)}")
            
            # Check if categoria is correctly returned
            if fetched_ingredient.get('categoria') == "Frutas":
                print("✅ Categoria field is correctly returned on GET")
            else:
                print(f"❌ Categoria field is not correctly returned on GET. Value: {fetched_ingredient.get('categoria')}")
            
            # 4. Delete the test ingredient
            print(f"\n4. Deleting test ingredient with ID: {ingredient_id}...")
            response = requests.delete(f"{base_url}/ingredientes/{ingredient_id}")
            if response.status_code == 200:
                print("✅ Test ingredient deleted successfully")
            else:
                print(f"❌ Failed to delete test ingredient: {response.content}")
        else:
            print("❌ Failed to get ID of created ingredient")
    except requests.exceptions.RequestException as e:
        print(f"❌ API request failed: {e}")
    except Exception as e:
        print(f"❌ Test failed: {e}")

def test_categoria_direct_db():
    """Test if the categoria field works correctly through direct database access"""
    print("\nTesting categoria field with direct database access...")
    
    # Get the database path
    base_dir = os.path.dirname(os.path.abspath(__file__))
    instance_dir = os.path.join(os.path.dirname(base_dir), 'instance')
    db_path = os.path.join(instance_dir, 'inventario_zombie.sqlite')
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check if tabla Ingredientes exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Ingredientes'")
        if not cursor.fetchone():
            print("❌ Ingredientes table does not exist!")
            return
        
        # Check if categoria column exists
        cursor.execute("PRAGMA table_info(Ingredientes)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'categoria' in columns:
            print("✅ 'categoria' column exists in Ingredientes table")
        else:
            print("❌ 'categoria' column does not exist in Ingredientes table")
            return
        
        # Insert a test ingredient directly
        test_name = f"DB Test Ingredient {int(time.time())}"
        cursor.execute(
            "INSERT INTO Ingredientes (nombre, unidad_medida, precio_compra, cantidad_actual, stock_minimo, categoria) VALUES (?, ?, ?, ?, ?, ?)",
            (test_name, "kg", 20.0, 10.0, 5.0, "Cereales")
        )
        conn.commit()
        
        ingredient_id = cursor.lastrowid
        print(f"✅ Test ingredient created with ID: {ingredient_id}")
        
        # Verify the ingredient was created with the correct categoria
        cursor.execute("SELECT * FROM Ingredientes WHERE id = ?", (ingredient_id,))
        ingredient = cursor.fetchone()
        
        if ingredient:
            print(f"✅ Retrieved ingredient from database: {dict(ingredient)}")
            
            if ingredient['categoria'] == "Cereales":
                print("✅ Categoria field was saved correctly in database")
            else:
                print(f"❌ Categoria field was not saved correctly in database. Value: {ingredient['categoria']}")
            
            # Clean up - delete the test ingredient
            cursor.execute("DELETE FROM Ingredientes WHERE id = ?", (ingredient_id,))
            conn.commit()
            print("✅ Test ingredient deleted from database")
        else:
            print("❌ Failed to retrieve test ingredient from database")
            
        conn.close()
            
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == '__main__':
    print("Starting categoria field tests...")
    test_categoria_direct_db()
    
    # Only run API tests if requested
    if len(sys.argv) > 1 and sys.argv[1] == '--api':
        test_categoria_api()
    else:
        print("\nSkipping API tests. Use --api flag to run them.")
        print("Note: API tests require the Flask app to be running.")
    
    print("\nTests completed!") 