from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from glutenix.api.deps import get_db
from glutenix.db.models import Application
from glutenix.schemas.models import ApplicationCreate, ApplicationResponse

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("", response_model=list[ApplicationResponse])
def list_applications(db: Session = Depends(get_db)):
    return db.query(Application).all()


@router.get("/{application_id}", response_model=ApplicationResponse)
def get_application(application_id: int, db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(404, detail="Application not found")
    return app


@router.post("", response_model=ApplicationResponse, status_code=201)
def create_application(body: ApplicationCreate, db: Session = Depends(get_db)):
    app = Application(**body.model_dump())
    db.add(app)
    db.commit()
    db.refresh(app)
    return app
