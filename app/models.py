from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

class Rack(Base):
    __tablename__ = "racks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    location = Column(String, nullable=True)
    height = Column(Integer, default=42)  # Standard 42U
    
    devices = relationship("Device", back_populates="rack", cascade="all, delete-orphan")

class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    device_type = Column(String) # e.g., "Switch", "Server", "Router"
    u_position = Column(Integer) # The bottom U number
    u_height = Column(Integer, default=1) # Height in U
    
    rack_id = Column(Integer, ForeignKey("racks.id"))
    rack = relationship("Rack", back_populates="devices")
    
    ports = relationship("Port", back_populates="device", cascade="all, delete-orphan")

class Port(Base):
    __tablename__ = "ports"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String) # e.g., "Eth1/1", "Gi0/1"
    device_id = Column(Integer, ForeignKey("devices.id"))
    
    device = relationship("Device", back_populates="ports")
    
    # Simple adjacency list for connections
    connected_to_id = Column(Integer, ForeignKey("ports.id"), nullable=True)
    connected_to = relationship("Port", remote_side=[id], backref="connected_from")
