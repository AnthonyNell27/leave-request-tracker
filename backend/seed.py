from database import SessionLocal
from models import Employee

db = SessionLocal()

employees = [
    Employee(name="Anna Cruz"),
    Employee(name="Juan Dela Cruz"),
    Employee(name="Maria Santos"),
    Employee(name="Jose Reyes"),
    Employee(name="Carla Garcia"),
]

db.add_all(employees)

db.commit()

db.close()

print("Employees seeded")