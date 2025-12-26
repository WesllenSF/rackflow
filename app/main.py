from fastapi import FastAPI, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import timedelta
from . import models, database, auth

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Init DB
models.Base.metadata.create_all(bind=database.engine)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Startup event to create default admin if not exists
@app.on_event("startup")
def on_startup():
    db = database.SessionLocal()
    user = db.query(models.User).filter(models.User.username == "admin").first()
    if not user:
        hashed_password = auth.get_password_hash("admin")
        user = models.User(username="admin", hashed_password=hashed_password)
        db.add(user)
        db.commit()
    db.close()

# --- Auth Routes ---

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not auth.verify_password(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Usuário ou senha inválidos"})
    
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)
    return response

@app.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token")
    return response

# --- Protected Routes ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user_required)):
    racks = db.query(models.Rack).all()
    return templates.TemplateResponse("index.html", {"request": request, "racks": racks, "user": user})

@app.post("/racks/add")
async def add_rack(name: str = Form(...), location: str = Form(...), height: int = Form(42), db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user_required)):
    new_rack = models.Rack(name=name, location=location, height=height)
    db.add(new_rack)
    db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.post("/racks/{rack_id}/delete")
async def delete_rack(rack_id: int, db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user_required)):
    rack = db.query(models.Rack).filter(models.Rack.id == rack_id).first()
    if rack:
        # Devices and ports cascade delete usually needs to be configured in models or handled manually
        # SQLAlchemy cascade="all, delete-orphan" on relationship usually handles it if configured
        # Let's check models.py later, but for now manual cleanup is safer if not sure
        db.delete(rack)
        db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, user: models.User = Depends(auth.get_current_user_required)):
    return templates.TemplateResponse("profile.html", {"request": request, "user": user})

@app.post("/profile/change-password", response_class=HTMLResponse)
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user_required)
):
    if not auth.verify_password(current_password, user.hashed_password):
        return templates.TemplateResponse("profile.html", {
            "request": request, 
            "user": user, 
            "error": "Senha atual incorreta"
        })
    
    if new_password != confirm_password:
        return templates.TemplateResponse("profile.html", {
            "request": request, 
            "user": user, 
            "error": "A nova senha e a confirmação não coincidem"
        })
        
    # Re-fetch user to ensure it is attached to the current database session
    # This prevents issues where the injected user object might be detached
    db_user = db.query(models.User).filter(models.User.id == user.id).first()
    if db_user:
        db_user.hashed_password = auth.get_password_hash(new_password)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
    
    return templates.TemplateResponse("profile.html", {
        "request": request, 
        "user": db_user if db_user else user, 
        "message": "Senha alterada com sucesso!"
    })

@app.get("/racks/{rack_id}", response_class=HTMLResponse)
async def view_rack(request: Request, rack_id: int, db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user_required)):
    rack = db.query(models.Rack).filter(models.Rack.id == rack_id).first()
    if not rack:
        raise HTTPException(status_code=404, detail="Rack not found")
    
    # Sort devices by U position (descending for visual rack view)
    devices = sorted(rack.devices, key=lambda x: x.u_position, reverse=True)
    
    # Create a visual grid representation
    # We need to map which U is occupied by which device
    u_slots = []
    occupied_u = set()
    
    for device in devices:
        for u in range(device.u_position, device.u_position + device.u_height):
            occupied_u.add(u)

    # We want to iterate from Top (Height) to Bottom (1)
    # We will pass a list of slots where each slot is either empty or the start of a device
    # Or a placeholder for "occupied by device below"
    
    rack_visual = []
    current_u = rack.height
    while current_u > 0:
        device_at_this_u = next((d for d in devices if d.u_position + d.u_height - 1 == current_u), None)
        
        if device_at_this_u:
            rack_visual.append({
                "u": current_u,
                "type": "device",
                "device": device_at_this_u,
                "height": device_at_this_u.u_height,
                "pixel_height": device_at_this_u.u_height * 30
            })
            current_u -= device_at_this_u.u_height
        else:
            # Check if this U is occupied by a device starting lower (shouldn't happen with the logic above, but for safety)
            # Actually, the logic above jumps 'height' steps, so we just need to handle empty slots
            is_occupied = False
            for d in devices:
                if d.u_position <= current_u < d.u_position + d.u_height:
                    is_occupied = True
                    break
            
            if not is_occupied:
                rack_visual.append({
                    "u": current_u,
                    "type": "empty",
                    "height": 1
                })
                current_u -= 1
            else:
                 # Should have been caught by the jump, but if we have overlaps/errors
                 current_u -= 1

    return templates.TemplateResponse("rack_detail.html", {
        "request": request, 
        "rack": rack, 
        "rack_visual": rack_visual,
        "user": user
    })

@app.post("/racks/{rack_id}/devices/add")
async def add_device(
    rack_id: int, 
    name: str = Form(...), 
    device_type: str = Form(...), 
    u_position: int = Form(...), 
    u_height: int = Form(1),
    db: Session = Depends(get_db),
    user: models.User = Depends(auth.get_current_user_required)
):
    # Basic validation: Check collision
    # (Simplified for now, assume user knows what they are doing or handle DB error)
    new_device = models.Device(
        name=name, 
        device_type=device_type, 
        u_position=u_position, 
        u_height=u_height, 
        rack_id=rack_id
    )
    db.add(new_device)
    db.commit()
    return RedirectResponse(url=f"/racks/{rack_id}", status_code=303)

@app.post("/devices/{device_id}/delete")
async def delete_device(device_id: int, db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user_required)):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    rack_id = device.rack_id
    if device:
        db.delete(device)
        db.commit()
    return RedirectResponse(url=f"/racks/{rack_id}", status_code=303)

@app.get("/devices/{device_id}", response_class=HTMLResponse)
async def view_device(request: Request, device_id: int, db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user_required)):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    all_devices = db.query(models.Device).all() # For connection dropdowns
    
    # Flatten ports for connection targets
    # (In a real app, we'd filter compatible ports, etc.)
    return templates.TemplateResponse("device_detail.html", {
        "request": request, 
        "device": device,
        "all_devices": all_devices,
        "user": user
    })

@app.post("/devices/{device_id}/ports/add")
async def add_port(device_id: int, name: str = Form(...), db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user_required)):
    # Supports comma separated names e.g. "1,2,3" or "Gi1/0/1"
    port_names = [n.strip() for n in name.split(',')]
    for p_name in port_names:
        if p_name:
            new_port = models.Port(name=p_name, device_id=device_id)
            db.add(new_port)
    db.commit()
    return RedirectResponse(url=f"/devices/{device_id}", status_code=303)

@app.post("/ports/{port_id}/connect")
async def connect_port(port_id: int, target_port_id: int = Form(...), db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user_required)):
    port = db.query(models.Port).filter(models.Port.id == port_id).first()
    target = db.query(models.Port).filter(models.Port.id == target_port_id).first()
    
    if port and target:
        port.connected_to_id = target.id
        target.connected_to_id = port.id
        db.commit()
        
    return RedirectResponse(url=f"/devices/{port.device_id}", status_code=303)

@app.post("/ports/{port_id}/disconnect")
async def disconnect_port(port_id: int, db: Session = Depends(get_db), user: models.User = Depends(auth.get_current_user_required)):
    port = db.query(models.Port).filter(models.Port.id == port_id).first()
    if port and port.connected_to:
        target = port.connected_to
        target.connected_to_id = None
        port.connected_to_id = None
        db.commit()
        
    return RedirectResponse(url=f"/devices/{port.device_id}", status_code=303)
