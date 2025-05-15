import sqlite3
import datetime
import math
from collections import defaultdict
from database import get_db_connection

class SalesPredictor:
    """
    Class to predict sales based on historical data.
    Uses the day of the week pattern to make predictions.
    """
    
    def __init__(self, db_connection=None):
        """
        Initialize the SalesPredictor with an optional database connection.
        
        Args:
            db_connection: An optional database connection. If not provided,
                           a new connection will be created.
        """
        self.conn = db_connection if db_connection else get_db_connection()
        self.REQUIRED_DAYS = 4  # Constante para el número de días requeridos
    
    def close(self):
        """Close the database connection if it was created by this instance."""
        if self.conn and not isinstance(self.conn, sqlite3.Connection):
            self.conn.close()
    
    def get_weekday_from_date(self, date_str):
        """
        Get the weekday (0-6) from a date string in 'YYYY-MM-DD' format.
        0 is Monday, 6 is Sunday.
        """
        date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.weekday()
    
    def get_date_name(self, weekday):
        """
        Get the name of the weekday in Spanish.
        """
        days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        return days[weekday]
    
    def get_historical_sales_by_weekday(self, target_weekday, num_weeks=4, category=None, article=None):
        """
        Get historical sales data for a specific weekday, ensuring exactly REQUIRED_DAYS days with sales.
        
        Args:
            target_weekday: The weekday (0-6) to get sales for.
            num_weeks: Initial number of weeks to look back.
            category: Optional category filter.
            article: Optional article filter.
            
        Returns:
            A tuple containing:
            - List of dictionaries containing the historical sales data
            - Number of weeks actually analyzed to find REQUIRED_DAYS days with sales
        """
        cursor = self.conn.cursor()
        
        # Get current date
        current_date = datetime.datetime.now().date()
        
        # Initialize variables for finding valid sales days
        valid_sales_days = []
        date_to_check = current_date
        max_days_back = 180  # Máximo de días para buscar hacia atrás (6 meses)
        days_checked = 0
        weeks_analyzed = 0
        
        # Go back in time until we find exactly REQUIRED_DAYS days with sales or hit the limit
        while len(valid_sales_days) < self.REQUIRED_DAYS and days_checked < max_days_back:
            date_to_check -= datetime.timedelta(days=1)
            days_checked += 1
            
            # Only check days that match our target weekday
            if date_to_check.weekday() == target_weekday:
                weeks_analyzed += 1
                date_str = date_to_check.strftime('%Y-%m-%d')
                
                # Build query to check if this day has sales
                query = """
                    SELECT fecha, articulo, categoria, subcategoria, 
                           SUM(articulos_vendidos) as total_vendidos 
                    FROM Ventas 
                    WHERE fecha = ?
                """
                params = [date_str]
                
                if category:
                    query += " AND categoria = ?"
                    params.append(category)
                
                if article:
                    query += " AND articulo = ?"
                    params.append(article)
                
                query += " GROUP BY fecha, articulo, categoria, subcategoria"
                
                cursor.execute(query, params)
                day_sales = cursor.fetchall()
                
                # If we found sales for this day, add it to our valid days
                if day_sales:
                    valid_sales_days.append({
                        'date': date_str,
                        'sales': [dict(row) for row in day_sales]
                    })
        
        # If we didn't find enough days with sales, raise an exception
        if len(valid_sales_days) < self.REQUIRED_DAYS:
            raise Exception(f"No se encontraron suficientes días con ventas. Se requieren {self.REQUIRED_DAYS} días pero solo se encontraron {len(valid_sales_days)}.")
        
        # Flatten and process the results
        results = []
        for day in valid_sales_days:
            for sale in day['sales']:
                # Include subcategoria (variant) in the results
                results.append({
                    'fecha': sale['fecha'],
                    'articulo': sale['articulo'],
                    'categoria': sale['categoria'],
                    'subcategoria': sale['subcategoria'],
                    'total_vendidos': sale['total_vendidos']
                })
        
        return results, weeks_analyzed
    
    def predict_sales_for_weekday(self, target_weekday, num_weeks=4, category=None, article=None):
        """
        Predict sales for a specific weekday based on historical data.
        
        Args:
            target_weekday: The weekday (0-6) to predict sales for.
            num_weeks: Initial number of weeks to look back.
            category: Optional category filter.
            article: Optional article filter.
            
        Returns:
            A tuple containing:
            - Dictionary with predicted sales by article and variant
            - Number of weeks actually analyzed
        """
        historical_sales, weeks_analyzed = self.get_historical_sales_by_weekday(
            target_weekday, num_weeks, category, article
        )
        
        # Group by article and variant
        article_variant_sales = defaultdict(lambda: defaultdict(list))
        for sale in historical_sales:
            key = sale['articulo']
            variant = sale['subcategoria'] or 'default'
            article_variant_sales[key][variant].append(sale['total_vendidos'])
        
        # Calculate predictions
        predictions = {}
        for article, variants in article_variant_sales.items():
            predictions[article] = {
                'variants': {},
                'total_predicted': 0
            }
            
            for variant, sales in variants.items():
                if len(sales) > 0:
                    # Calcular promedio dividiendo siempre entre REQUIRED_DAYS (4), no entre len(sales)
                    total_sales = sum(sales)
                    avg_sales = total_sales / self.REQUIRED_DAYS
                    variant_prediction = {
                        'predicted_sales': math.ceil(avg_sales),
                        'historical_data': sales,
                        'num_days': len(sales),
                        'days_with_sales': len(sales),
                        'total_historical': total_sales
                    }
                    
                    if variant == 'default':
                        predictions[article].update(variant_prediction)
                    else:
                        predictions[article]['variants'][variant] = variant_prediction
                        predictions[article]['total_predicted'] += variant_prediction['predicted_sales']
            
            # Add the default variant to total if it exists
            if 'predicted_sales' in predictions[article]:
                predictions[article]['total_predicted'] += predictions[article]['predicted_sales']
        
        return predictions, weeks_analyzed
    
    def predict_sales_for_date(self, target_date, num_weeks=4, category=None, article=None):
        """
        Predict sales for a specific date based on historical data for the same weekday.
        
        Args:
            target_date: The date (YYYY-MM-DD) to predict sales for.
            num_weeks: Initial number of weeks to look back.
            category: Optional category filter.
            article: Optional article filter.
            
        Returns:
            A dictionary with prediction results.
        """
        # Get weekday from the target date
        weekday = self.get_weekday_from_date(target_date)
        weekday_name = self.get_date_name(weekday)
        
        # Get predictions
        predictions, weeks_analyzed = self.predict_sales_for_weekday(weekday, num_weeks, category, article)
        
        # Calculate total predicted sales across all articles and variants
        total_predicted = sum(item['total_predicted'] for item in predictions.values())
        
        # Return results with metadata
        return {
            'target_date': target_date,
            'weekday': weekday,
            'weekday_name': weekday_name,
            'predictions': predictions,
            'total_predicted': math.ceil(total_predicted),
            'num_weeks_analyzed': weeks_analyzed,
            'days_with_sales': self.REQUIRED_DAYS  # Ahora siempre será 4
        }

def get_sales_predictor():
    """Helper function to get a SalesPredictor instance."""
    return SalesPredictor() 