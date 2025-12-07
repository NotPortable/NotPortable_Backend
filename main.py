from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
import os
import re

# FastAPI 앱
app = FastAPI(title="NotPortable API", version="1.0.0")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 데이터베이스 설정 (jungwoo 사용자로 변경)
DATABASE_URL = "mysql+pymysql://jungwoo:gamepassword@localhost/game_logs"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 모델 정의
class NeverballLog(Base):
    __tablename__ = "neverball_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), index=True)
    level = Column(Integer)
    score = Column(Integer)
    coins = Column(Integer)
    time = Column(String(20))
    is_anomaly = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

class SuperTuxLog(Base):
    __tablename__ = "supertux_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), index=True)
    level = Column(String(50))
    coins = Column(Integer)
    secrets = Column(Integer)
    time = Column(Float)
    is_anomaly = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

class ETRLog(Base):
    __tablename__ = "etr_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), index=True)
    course = Column(String(100))
    score = Column(Integer)
    herring = Column(Integer)
    time = Column(String(20))
    is_anomaly = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

# 테이블 생성
Base.metadata.create_all(bind=engine)

# Pydantic 모델
class NeverballData(BaseModel):
    username: str
    level: int
    score: int
    coins: int
    time: str
    is_anomaly: bool = False

class SuperTuxData(BaseModel):
    username: str
    level: str
    coins: int
    secrets: int
    time: float
    is_anomaly: bool = False

class ETRData(BaseModel):
    username: str
    course: str
    score: int
    herring: int
    time: str
    is_anomaly: bool = False

class LoginRequest(BaseModel):
    username: str
    password: str

class RankingResponse(BaseModel):
    rank: int
    username: str
    score: int
    additional_info: dict

# 의존성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 로그인 엔드포인트
@app.post("/api/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    # 게임 로그에서 사용자 이름 확인
    neverball_user = db.query(NeverballLog).filter(NeverballLog.username == request.username).first()
    supertux_user = db.query(SuperTuxLog).filter(SuperTuxLog.username == request.username).first()
    etr_user = db.query(ETRLog).filter(ETRLog.username == request.username).first()
    
    if neverball_user or supertux_user or etr_user:
        return {
            "success": True,
            "username": request.username,
            "message": "로그인 성공"
        }
    else:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다")

# Neverball 로그 추가
@app.post("/api/neverball/log")
async def add_neverball_log(data: NeverballData, db: Session = Depends(get_db)):
    log = NeverballLog(**data.dict())
    db.add(log)
    db.commit()
    db.refresh(log)
    return {"success": True, "id": log.id}

# Neverball 랭킹 조회
@app.get("/api/neverball/ranking")
async def get_neverball_ranking(limit: int = 10, db: Session = Depends(get_db)):
    logs = db.query(NeverballLog).order_by(NeverballLog.score.desc()).limit(limit).all()
    
    ranking = []
    for idx, log in enumerate(logs, 1):
        ranking.append({
            "rank": idx,
            "username": log.username,
            "score": log.score,
            "level": log.level,
            "coins": log.coins,
            "time": log.time,
            "is_anomaly": log.is_anomaly,
            "created_at": log.created_at.isoformat()
        })
    
    return ranking

# 사용자별 Neverball 기록
@app.get("/api/neverball/user/{username}")
async def get_neverball_user_stats(username: str, db: Session = Depends(get_db)):
    logs = db.query(NeverballLog).filter(NeverballLog.username == username).order_by(NeverballLog.created_at.desc()).all()
    
    if not logs:
        raise HTTPException(status_code=404, detail="사용자 기록을 찾을 수 없습니다")
    
    # 통계 계산
    total_plays = len(logs)
    max_score = max([log.score for log in logs])
    avg_coins = sum([log.coins for log in logs]) / total_plays
    max_level = max([log.level for log in logs])
    
    recent_logs = []
    for log in logs[:10]:
        recent_logs.append({
            "level": log.level,
            "score": log.score,
            "coins": log.coins,
            "time": log.time,
            "is_anomaly": log.is_anomaly,
            "created_at": log.created_at.isoformat()
        })
    
    return {
        "username": username,
        "stats": {
            "total_plays": total_plays,
            "max_score": max_score,
            "avg_coins": int(avg_coins),
            "max_level": max_level
        },
        "recent_logs": recent_logs
    }

# SuperTux 로그 추가
@app.post("/api/supertux/log")
async def add_supertux_log(data: SuperTuxData, db: Session = Depends(get_db)):
    log = SuperTuxLog(**data.dict())
    db.add(log)
    db.commit()
    db.refresh(log)
    return {"success": True, "id": log.id}

# SuperTux 랭킹 조회
@app.get("/api/supertux/ranking")
async def get_supertux_ranking(limit: int = 10, db: Session = Depends(get_db)):
    logs = db.query(SuperTuxLog).order_by(SuperTuxLog.coins.desc()).limit(limit).all()
    
    ranking = []
    for idx, log in enumerate(logs, 1):
        ranking.append({
            "rank": idx,
            "username": log.username,
            "level": log.level,
            "coins": log.coins,
            "secrets": log.secrets,
            "time": log.time,
            "is_anomaly": log.is_anomaly,
            "created_at": log.created_at.isoformat()
        })
    
    return ranking

# 사용자별 SuperTux 기록
@app.get("/api/supertux/user/{username}")
async def get_supertux_user_stats(username: str, db: Session = Depends(get_db)):
    logs = db.query(SuperTuxLog).filter(SuperTuxLog.username == username).order_by(SuperTuxLog.created_at.desc()).all()
    
    if not logs:
        raise HTTPException(status_code=404, detail="사용자 기록을 찾을 수 없습니다")
    
    total_plays = len(logs)
    total_coins = sum([log.coins for log in logs])
    total_secrets = sum([log.secrets for log in logs])
    
    recent_logs = []
    for log in logs[:10]:
        recent_logs.append({
            "level": log.level,
            "coins": log.coins,
            "secrets": log.secrets,
            "time": log.time,
            "is_anomaly": log.is_anomaly,
            "created_at": log.created_at.isoformat()
        })
    
    return {
        "username": username,
        "stats": {
            "total_plays": total_plays,
            "total_coins": total_coins,
            "total_secrets": total_secrets
        },
        "recent_logs": recent_logs
    }

# ETR 로그 추가
@app.post("/api/etr/log")
async def add_etr_log(data: ETRData, db: Session = Depends(get_db)):
    log = ETRLog(**data.dict())
    db.add(log)
    db.commit()
    db.refresh(log)
    return {"success": True, "id": log.id}

# ETR 랭킹 조회
@app.get("/api/etr/ranking")
async def get_etr_ranking(limit: int = 10, db: Session = Depends(get_db)):
    logs = db.query(ETRLog).order_by(ETRLog.score.desc()).limit(limit).all()
    
    ranking = []
    for idx, log in enumerate(logs, 1):
        ranking.append({
            "rank": idx,
            "username": log.username,
            "course": log.course,
            "score": log.score,
            "herring": log.herring,
            "time": log.time,
            "is_anomaly": log.is_anomaly,
            "created_at": log.created_at.isoformat()
        })
    
    return ranking

# 사용자별 ETR 기록
@app.get("/api/etr/user/{username}")
async def get_etr_user_stats(username: str, db: Session = Depends(get_db)):
    logs = db.query(ETRLog).filter(ETRLog.username == username).order_by(ETRLog.created_at.desc()).all()
    
    if not logs:
        raise HTTPException(status_code=404, detail="사용자 기록을 찾을 수 없습니다")
    
    total_plays = len(logs)
    max_score = max([log.score for log in logs])
    total_herring = sum([log.herring for log in logs])
    
    recent_logs = []
    for log in logs[:10]:
        recent_logs.append({
            "course": log.course,
            "score": log.score,
            "herring": log.herring,
            "time": log.time,
            "is_anomaly": log.is_anomaly,
            "created_at": log.created_at.isoformat()
        })
    
    return {
        "username": username,
        "stats": {
            "total_plays": total_plays,
            "max_score": max_score,
            "total_herring": total_herring
        },
        "recent_logs": recent_logs
    }

# 이상 데이터 조회
@app.get("/api/anomalies")
async def get_anomalies(db: Session = Depends(get_db)):
    neverball_anomalies = db.query(NeverballLog).filter(NeverballLog.is_anomaly == True).order_by(NeverballLog.created_at.desc()).limit(10).all()
    supertux_anomalies = db.query(SuperTuxLog).filter(SuperTuxLog.is_anomaly == True).order_by(SuperTuxLog.created_at.desc()).limit(10).all()
    etr_anomalies = db.query(ETRLog).filter(ETRLog.is_anomaly == True).order_by(ETRLog.created_at.desc()).limit(10).all()
    
    return {
        "neverball": [{"username": log.username, "score": log.score, "created_at": log.created_at.isoformat()} for log in neverball_anomalies],
        "supertux": [{"username": log.username, "coins": log.coins, "created_at": log.created_at.isoformat()} for log in supertux_anomalies],
        "etr": [{"username": log.username, "score": log.score, "created_at": log.created_at.isoformat()} for log in etr_anomalies]
    }

# 헬스 체크
@app.get("/")
async def root():
    return {"status": "ok", "message": "NotPortable API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)