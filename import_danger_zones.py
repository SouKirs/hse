import geopandas as gpd
from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape
from main import SessionLocal, DangerZone

# 1. Загружаем GeoJSON
geo_df = gpd.read_file("danger_zones.geojson")

# 2. Создаем сессию
db: Session = SessionLocal()

try:
    for polygon in geo_df['geometry']:
        dz = DangerZone(polygon=from_shape(polygon, srid=4326))
        db.add(dz)
    db.commit()
    print(f"Добавлено {len(geo_df)} опасных зон")
except Exception as e:
    db.rollback()
    print("Ошибка при добавлении данных:", e)
finally:
    db.close()
