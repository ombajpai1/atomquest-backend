import datetime
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
import models, auth

Base.metadata.create_all(bind=engine)

def seed_data(db_session=None):
    db = db_session or SessionLocal()
    try:
        if db.query(models.User).first():
            print("Database already seeded.")
            return

        print("Seeding users...")
        admin = models.User(name="Admin User", email="admin@company.com", hashed_password=auth.get_password_hash("Admin@123"), role="admin", department="IT")
        manager = models.User(name="Manager User", email="manager@company.com", hashed_password=auth.get_password_hash("Manager@123"), role="manager", department="Engineering")
        db.add_all([admin, manager])
        db.commit()

        emp1 = models.User(name="Employee One", email="emp1@company.com", hashed_password=auth.get_password_hash("Emp@123"), role="employee", manager_id=manager.id, department="Engineering")
        emp2 = models.User(name="Employee Two", email="emp2@company.com", hashed_password=auth.get_password_hash("Emp@123"), role="employee", manager_id=manager.id, department="Engineering")
        db.add_all([emp1, emp2])
        db.commit()

        print("Seeding cycle config...")
        year = datetime.datetime.now().year
        cycle = models.CycleConfig(
            cycle_year=year,
            goal_setting_open=datetime.date(year, 1, 1),
            q1_open=datetime.date(year, 3, 1),
            q2_open=datetime.date(year, 6, 1),
            q3_open=datetime.date(year, 9, 1),
            q4_open=datetime.date(year, 12, 1),
            is_active=True
        )
        db.add(cycle)
        db.commit()

        print("Seeding goal sheets & goals...")
        # Emp1 - draft goals
        sheet1 = models.GoalSheet(employee_id=emp1.id, cycle_year=year, status="draft")
        db.add(sheet1)
        db.commit()

        g1 = models.Goal(goal_sheet_id=sheet1.id, thrust_area="Revenue", title="Increase sales", description="Increase Q1 sales by 20%", uom_type="min", target_value=120000, weightage=30)
        g2 = models.Goal(goal_sheet_id=sheet1.id, thrust_area="Operations", title="Reduce costs", description="Cut down operational costs", uom_type="max", target_value=50000, weightage=40)
        db.add_all([g1, g2])
        db.commit()

        # Emp2 - approved goals & achievements
        sheet2 = models.GoalSheet(employee_id=emp2.id, cycle_year=year, status="approved", approved_at=datetime.datetime.utcnow(), approved_by=manager.id)
        db.add(sheet2)
        db.commit()

        g3 = models.Goal(goal_sheet_id=sheet2.id, thrust_area="Delivery", title="Ship v1.0", description="Ship the main product", uom_type="timeline", target_date=datetime.date(year, 6, 30), weightage=100)
        db.add(g3)
        db.commit()

        ach1 = models.Achievement(goal_id=g3.id, quarter="Q1", actual_value=0, actual_date=datetime.date(year, 3, 15), status="on_track")
        db.add(ach1)
        db.commit()

        print("Seed complete.")
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
