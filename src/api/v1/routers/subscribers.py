from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.v1.schemas.subscriber import (
    SubscriberResponse, SubscriberContactCreate, SubscriberContactResponse,
    SubscriberUpdateActive
)
from src.api.v1.services.subscriber_service import SubscriberService
from src.shared.database import get_db

router = APIRouter(prefix="/subscribers", tags=["subscribers"])

async def get_subscriber_service(db: AsyncSession = Depends(get_db)) -> SubscriberService:
    return SubscriberService(db)

# ----- Subscriber endpoints -----
@router.post("/", response_model=SubscriberResponse, status_code=status.HTTP_201_CREATED)
async def create_subscriber(service: SubscriberService = Depends(get_subscriber_service)):
    subscriber = await service.create_subscriber()
    return subscriber

@router.get("/{subscriber_id}", response_model=SubscriberResponse)
async def get_subscriber(subscriber_id: int, service: SubscriberService = Depends(get_subscriber_service)):
    subscriber = await service.get_subscriber(subscriber_id)
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return subscriber

@router.patch("/{subscriber_id}", response_model=SubscriberResponse)
async def update_subscriber_active(
    subscriber_id: int,
    data: SubscriberUpdateActive,
    service: SubscriberService = Depends(get_subscriber_service)
):
    subscriber = await service.update_active(subscriber_id, data.is_active)
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return subscriber

@router.delete("/{subscriber_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscriber(subscriber_id: int, service: SubscriberService = Depends(get_subscriber_service)):
    deleted = await service.delete_subscriber(subscriber_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Subscriber not found")

@router.get("/", response_model=list[SubscriberResponse])
async def list_subscribers(
    skip: int = 0, limit: int = 100,
    service: SubscriberService = Depends(get_subscriber_service)
):
    return await service.list_subscribers(skip, limit)

# ----- Contacts endpoints -----
@router.post("/{subscriber_id}/contacts", response_model=SubscriberContactResponse, status_code=status.HTTP_201_CREATED)
async def add_contact(
    subscriber_id: int,
    contact_data: SubscriberContactCreate,
    service: SubscriberService = Depends(get_subscriber_service)
):
    contact = await service.add_contact(
        subscriber_id,
        contact_data.channel,
        contact_data.contact,
        contact_data.is_verified
    )
    if not contact:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return contact

@router.get("/{subscriber_id}/contacts", response_model=list[SubscriberContactResponse])
async def get_contacts(subscriber_id: int, service: SubscriberService = Depends(get_subscriber_service)):
    subscriber = await service.get_subscriber(subscriber_id)
    if not subscriber:
        raise HTTPException(status_code=404, detail="Subscriber not found")
    return await service.get_contacts(subscriber_id)

@router.put("/contacts/{contact_id}", response_model=SubscriberContactResponse)
async def update_contact(
    contact_id: int,
    update_data: SubscriberContactCreate, # TODO
    service: SubscriberService = Depends(get_subscriber_service)
):
    updated = await service.update_contact(
        contact_id,
        channel=update_data.channel,
        contact=update_data.contact,
        is_verified=update_data.is_verified
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Contact not found")
    return updated

@router.delete("/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(contact_id: int, service: SubscriberService = Depends(get_subscriber_service)):
    deleted = await service.delete_contact(contact_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Contact not found")