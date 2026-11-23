from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.errors import AppError
from app.models import Property, PropertyAlias, Review
from app.schemas.common import DataResponse
from app.schemas.properties import (
    AliasCreate,
    AliasRead,
    PropertyCreate,
    PropertyRead,
    PropertyUpdate,
)
from app.services.ingestion.normalise import normalise_for_match
from app.services.properties import PropertyIndex, make_code

router = APIRouter(prefix="/properties", tags=["properties"])


def _counts(db: Session) -> dict[int, tuple[int, int]]:
    rows = db.execute(
        select(Review.property_id, Review.is_synthetic, func.count()).group_by(
            Review.property_id, Review.is_synthetic
        )
    ).all()
    counts: dict[int, list[int]] = {}
    for property_id, synthetic, count in rows:
        counts.setdefault(property_id, [0, 0])[1 if synthetic else 0] = count
    return {k: (v[0], v[1]) for k, v in counts.items()}


def _read(prop: Property, counts: dict[int, tuple[int, int]]) -> PropertyRead:
    real, synthetic = counts.get(prop.id, (0, 0))
    return PropertyRead(
        id=prop.id,
        code=prop.code,
        name=prop.name,
        location=prop.location,
        is_active=prop.is_active,
        review_count=real,
        synthetic_review_count=synthetic,
        aliases=[AliasRead.model_validate(a) for a in prop.aliases],
    )


def _get(db: Session, property_id: int) -> Property:
    # populate_existing: sessions keep objects after commit, so refresh aliases from the database.
    prop = db.get(
        Property, property_id, options=[selectinload(Property.aliases)], populate_existing=True
    )
    if prop is None:
        raise AppError(404, "PROPERTY_NOT_FOUND", f"Property {property_id} does not exist.")
    return prop


@router.get("", response_model=DataResponse[list[PropertyRead]])
def list_properties(db: Session = Depends(get_db)) -> DataResponse[list[PropertyRead]]:
    counts = _counts(db)
    props = db.scalars(
        select(Property).options(selectinload(Property.aliases)).order_by(Property.name)
    ).all()
    return DataResponse(data=[_read(p, counts) for p in props])


@router.get("/{property_id}", response_model=DataResponse[PropertyRead])
def get_property(property_id: int, db: Session = Depends(get_db)) -> DataResponse[PropertyRead]:
    return DataResponse(data=_read(_get(db, property_id), _counts(db)))


@router.post("", response_model=DataResponse[PropertyRead], status_code=201)
def create_property(
    body: PropertyCreate, db: Session = Depends(get_db)
) -> DataResponse[PropertyRead]:
    existing_codes = set(db.scalars(select(Property.code)))
    if body.code and body.code in existing_codes:
        raise AppError(
            409, "PROPERTY_EXISTS", f"A property with code '{body.code}' already exists."
        )
    if PropertyIndex(db).exact(body.name):
        raise AppError(
            409, "PROPERTY_EXISTS", f"A property or alias named '{body.name}' already exists."
        )
    prop = Property(
        name=body.name,
        code=body.code or make_code(body.name, existing_codes),
        location=body.location,
    )
    db.add(prop)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(
            409, "PROPERTY_EXISTS", "A property with that name already exists."
        ) from None
    db.refresh(prop)
    return DataResponse(data=_read(_get(db, prop.id), _counts(db)))


@router.patch("/{property_id}", response_model=DataResponse[PropertyRead])
def update_property(
    property_id: int, body: PropertyUpdate, db: Session = Depends(get_db)
) -> DataResponse[PropertyRead]:
    prop = _get(db, property_id)
    changes = body.model_dump(exclude_unset=True)
    if "name" in changes and changes["name"] is not None:
        match = PropertyIndex(db).exact(changes["name"])
        if match and match.property_id != prop.id:
            raise AppError(409, "PROPERTY_EXISTS", f"'{changes['name']}' is already in use.")
        prop.name = changes["name"]
    if "location" in changes:
        prop.location = changes["location"]
    if changes.get("is_active") is not None:
        prop.is_active = changes["is_active"]
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(
            409, "PROPERTY_EXISTS", "A property with that name already exists."
        ) from None
    return DataResponse(data=_read(_get(db, property_id), _counts(db)))


@router.post("/{property_id}/aliases", response_model=DataResponse[PropertyRead], status_code=201)
def add_alias(
    property_id: int, body: AliasCreate, db: Session = Depends(get_db)
) -> DataResponse[PropertyRead]:
    prop = _get(db, property_id)
    key = normalise_for_match(body.alias)
    if not key:
        raise AppError(422, "VALIDATION_ERROR", "The alias must contain letters or digits.")
    match = PropertyIndex(db).exact(body.alias)
    if match:
        raise AppError(409, "ALIAS_EXISTS", f"'{body.alias}' already refers to a property.")
    db.add(PropertyAlias(property_id=prop.id, alias_normalised=key[:200]))
    db.commit()
    return DataResponse(data=_read(_get(db, property_id), _counts(db)))


@router.delete("/{property_id}/aliases/{alias_id}", status_code=204)
def delete_alias(property_id: int, alias_id: int, db: Session = Depends(get_db)) -> Response:
    alias = db.get(PropertyAlias, alias_id)
    if alias is None or alias.property_id != property_id:
        raise AppError(
            404, "ALIAS_NOT_FOUND", f"Alias {alias_id} does not exist for this property."
        )
    db.delete(alias)
    db.commit()
    return Response(status_code=204)
