import sqlite3
import json
from datetime import datetime
import os
from PyQt5.QtCore import QObject, pyqtSignal
import threading
from utils.json_utils import serialize_json_safely, parse_json_safely

class DBManager(QObject):
    _instance = None
    _lock = threading.Lock()
    DEFAULT_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'test.db')
    
    # 시그널 정의
    db_changed = pyqtSignal(str)
    db_error = pyqtSignal(str)
    roi_settings_changed = pyqtSignal(str)
    roi_settings_updated = pyqtSignal(str)  # product_id를 인자로 전달
    
    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DBManager, cls).__new__(cls)
                cls._instance._db_path = None
                cls._instance._initialized = False
                cls._instance._connection = None
                cls._instance._connection_lock = threading.Lock()
                cls._instance._in_transaction = False
        return cls._instance
    
    def __init__(self, db_path=None):
        if self._initialized:
            return
            
        super().__init__()
        self._db_path = db_path or self.DEFAULT_DB_PATH
        self._ensure_db_exists()
        self._initialized = True
    
    def __del__(self):
        self.close_connection()
    
    @property
    def db_path(self):
        return self._db_path
    
    @db_path.setter
    def db_path(self, value):
        if value != self._db_path:
            self.close_connection()
            self._db_path = value
    
    def _get_connection(self):
        """DB 연결 획득 (자동 재연결)"""
        with self._connection_lock:
            try:
                # 연결 테스트
                if self._connection:
                    self._connection.execute("SELECT 1")
                    return self._connection
            except (sqlite3.Error, AttributeError):
                # 연결이 끊어진 경우 재연결
                try:
                    if self._connection:
                        self._connection.close()
                except:
                    pass
                self._connection = None

            # 새 연결 생성
            try:
                self._connection = sqlite3.connect(self._db_path)
                self._connection.row_factory = sqlite3.Row
                return self._connection
            except sqlite3.Error as e:
                self.db_error.emit(f"DB 연결 실패: {str(e)}")
                raise
    
    def begin_transaction(self):
        """트랜잭션 시작"""
        if not self._in_transaction:
            conn = self._get_connection()
            conn.execute("BEGIN")
            self._in_transaction = True

    def commit_transaction(self):
        """트랜잭션 커밋"""
        if self._in_transaction:
            conn = self._get_connection()
            conn.commit()
            self._in_transaction = False

    def rollback_transaction(self):
        """트랜잭션 롤백"""
        if self._in_transaction:
            conn = self._get_connection()
            conn.rollback()
            self._in_transaction = False
    
    def close_connection(self):
        """연결 종료"""
        with self._connection_lock:
            if self._connection:
                try:
                    if self._in_transaction:
                        self.rollback_transaction()
                    self._connection.close()
                except sqlite3.Error:
                    pass
                finally:
                    self._connection = None
    
    def execute_query(self, query, params=None):
        """쿼리 실행 (자동 재연결 포함)"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if not self._in_transaction:
                conn.commit()
            return cursor
        except sqlite3.Error as e:
            if not self._in_transaction:
                self.rollback_transaction()
            self.db_error.emit(f"쿼리 실행 실패: {str(e)}")
            raise
    
    def change_db(self, new_db_path):
        """DB 변경 (안전한 전환)"""
        try:
            if self._in_transaction:
                self.rollback_transaction()
                
            old_path = self._db_path
            old_connection = self._connection
            
            # 새 연결 테스트
            self._db_path = new_db_path
            test_connection = sqlite3.connect(new_db_path)
            test_connection.close()
            
            # 이전 연결 정리
            if old_connection:
                try:
                    old_connection.close()
                except:
                    pass
            
            self._connection = None
            self._ensure_db_exists()
            self.db_changed.emit(new_db_path)
            
        except Exception as e:
            self._db_path = old_path
            self._connection = old_connection
            self.db_error.emit(f"DB 변경 실패: {str(e)}")
            raise
    
    def _ensure_db_exists(self):
        """DB 파일 존재 확인 및 생성"""
        try:
            os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
            if not os.path.exists(self._db_path):
                self._initialize_db()
        except Exception as e:
            self.db_error.emit(f"DB 파일 생성 실패: {str(e)}")
            raise
    
    def _initialize_db(self):
        """DB 초기화 및 테이블 생성"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.executescript('''
                -- 장비 테이블
                CREATE TABLE IF NOT EXISTS equipment_table (
                    equipment_id TEXT PRIMARY KEY,
                    reg_date DATE,
                    equipment_name TEXT,
                    manager TEXT,
                    last_update TIMESTAMP
                );

                -- 제품 테이블
                CREATE TABLE IF NOT EXISTS product_table (
                    product_id TEXT PRIMARY KEY,
                    reg_date DATE,
                    product_name TEXT,
                    last_update TIMESTAMP,
                    test_items TEXT,
                    roi_settings TEXT DEFAULT '{}'  -- ROI 설정 JSON 형태로 저장
                );

                -- 생산 기록 테이블
                CREATE TABLE IF NOT EXISTS production_table (
                    production_date DATE,
                    product_id TEXT,
                    equipment_id TEXT,
                    production_count INTEGER DEFAULT 0,
                    defect_count INTEGER DEFAULT 0,
                    PRIMARY KEY (production_date, product_id, equipment_id),
                    FOREIGN KEY (product_id) REFERENCES product_table(product_id),
                    FOREIGN KEY (equipment_id) REFERENCES equipment_table(equipment_id)
                );

                -- 검사 결과 테이블
                CREATE TABLE IF NOT EXISTS inspection_result_table (
                    result_id TEXT PRIMARY KEY,
                    production_date DATE,
                    product_id TEXT,
                    equipment_id TEXT,
                    inspection_datetime TIMESTAMP,
                    roi_results TEXT,      -- JSON 형태로 ROI 결과 저장
                    image_path TEXT,
                    overall_result TEXT,
                    FOREIGN KEY (production_date, product_id, equipment_id) 
                        REFERENCES production_table(production_date, product_id, equipment_id)
                );
            ''')
            
            # 기본 데이터 삽입 (test.db인 경우)
            if self._db_path == self.DEFAULT_DB_PATH:
                cursor.executescript('''
                    INSERT OR IGNORE INTO equipment_table 
                    (equipment_id, reg_date, equipment_name, manager, last_update)
                    VALUES 
                    ('EQ001', date('now'), '기본 장비 1', '관리자', datetime('now')),
                    ('EQ002', date('now'), '기본 장비 2', '관리자', datetime('now'));
                    
                    INSERT OR IGNORE INTO product_table 
                    (product_id, reg_date, product_name, last_update, test_items, roi_settings)
                    VALUES 
                    ('PD001', date('now'), '기본 제품 1', datetime('now'), '{}', '{}'),
                    ('PD002', date('now'), '기본 제품 2', datetime('now'), '{}', '{}');
                ''')
            
            conn.commit()
            
        except sqlite3.Error as e:
            self.db_error.emit(f"DB 초기화 실패: {str(e)}")
            raise
    
    def insert_equipment(self, equipment_data):
        """장비 정보 저장"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO equipment_table 
                (equipment_id, reg_date, equipment_name, manager, last_update)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                equipment_data['equipment_id'],
                equipment_data['reg_date'],
                equipment_data['equipment_name'],
                equipment_data['manager'],
                equipment_data['last_update']
            ))
            
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"장비 정보 저장 중 오류 발생: {str(e)}")
            return False
        finally:
            conn.close()
    
    def insert_product(self, product_data):
        """제품 정보 저장"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO product_table 
                (product_id, reg_date, product_name, last_update, test_items, roi_settings)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                product_data['product_id'],
                datetime.now().date(),
                product_data['product_name'],
                datetime.now(),
                product_data.get('test_items', '{}'),
                product_data.get('roi_settings', '{}')
            ))
            
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"제품 정보 저장 중 오류 발생: {str(e)}")
            return False
        finally:
            conn.close()
    
    def insert_production(self, production_data):
        """생산 정보 저장"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO production_table 
                (production_date, product_id, equipment_id, production_count, defect_count)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                production_data['production_date'],
                production_data['product_id'],
                production_data['equipment_id'],
                production_data['production_count'],
                production_data['defect_count']
            ))
            
            conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"생산 정보 저장 중 오류 발생: {str(e)}")
            return False
        finally:
            conn.close()
    
    def insert_inspection_result(self, inspection_data):
        """검사 결과 저장"""
        try:
            # 트랜잭션 시작
            self.begin_transaction()
            
            # roi_results가 이미 문자열이면 그대로 사용, 아니면 직렬화
            roi_results = inspection_data['roi_results']
            if not isinstance(roi_results, str):
                roi_results = serialize_json_safely(roi_results)
            
            # 검사 결과 저장
            self.execute_query('''
                INSERT INTO inspection_result_table 
                (result_id, production_date, product_id, equipment_id,
                 inspection_datetime, roi_results, image_path, overall_result)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                inspection_data['result_id'],
                inspection_data['production_date'],
                inspection_data['product_id'],
                inspection_data['equipment_id'],
                inspection_data['inspection_datetime'],
                roi_results,
                inspection_data['image_path'],
                inspection_data['overall_result']
            ))
            
            self.commit_transaction()
            return True
            
        except sqlite3.Error as e:
            self.rollback_transaction()
            self.db_error.emit(f"검사 결과 저장 실패: {str(e)}")
            return False
    
    def update_or_insert_production(self, production_data):
        """생산 정보 업데이트 또는 삽입"""
        try:
            self.begin_transaction()
            
            cursor = self.execute_query('''
                SELECT production_count, defect_count 
                FROM production_table 
                WHERE production_date = ? 
                AND product_id = ? 
                AND equipment_id = ?
            ''', (
                production_data['production_date'],
                production_data['product_id'],
                production_data['equipment_id']
            ))
            
            if cursor.fetchone():
                # 기존 데이터 업데이트
                self.execute_query('''
                    UPDATE production_table 
                    SET production_count = ?,
                        defect_count = ?
                    WHERE production_date = ? 
                    AND product_id = ? 
                    AND equipment_id = ?
                ''', (
                    production_data['production_count'],
                    production_data['defect_count'],
                    production_data['production_date'],
                    production_data['product_id'],
                    production_data['equipment_id']
                ))
            else:
                # 새 데이터 삽입
                self.execute_query('''
                    INSERT INTO production_table 
                    (production_date, product_id, equipment_id, production_count, defect_count)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    production_data['production_date'],
                    production_data['product_id'],
                    production_data['equipment_id'],
                    production_data['production_count'],
                    production_data['defect_count']
                ))
            
            self.commit_transaction()
            return True
            
        except sqlite3.Error as e:
            self.rollback_transaction()
            self.db_error.emit(f"생산 정보 업데이트 실패: {str(e)}")
            return False
    
    def get_equipment_list(self):
        """등록된 모든 장비 목록을 조회합니다."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT equipment_id, equipment_name, registration_date
                FROM equipment_table
                ORDER BY registration_date DESC
            ''')
            
            # 결과를 딕셔너리 리스트로 변환
            equipment_list = []
            for row in cursor.fetchall():
                equipment_list.append({
                    'equipment_id': row[0],
                    'equipment_name': row[1],
                    'registration_date': row[2]
                })
            
            return equipment_list
        
        except sqlite3.Error as e:
            print(f"장비 목록 조회 중 오류 발생: {str(e)}")
            return []
        finally:
            conn.close()
    
    def get_product_list(self, equipment_id=None):
        """등록된 제품 목록을 조회합니다."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if equipment_id:
                cursor.execute('''
                    SELECT product_id, product_name, equipment_id, registration_date
                    FROM product_table
                    WHERE equipment_id = ?
                    ORDER BY registration_date DESC
                ''', (equipment_id,))
            else:
                cursor.execute('''
                    SELECT product_id, product_name, equipment_id, registration_date
                    FROM product_table
                    ORDER BY registration_date DESC
                ''')
            
            # 결과를 딕셔너리 리스트로 변환
            product_list = []
            for row in cursor.fetchall():
                product_list.append({
                    'product_id': row[0],
                    'product_name': row[1],
                    'equipment_id': row[2],
                    'registration_date': row[3]
                })
            
            return product_list
        
        except sqlite3.Error as e:
            print(f"제품 목록 조회 중 오류 발생: {str(e)}")
            return []
        finally:
            conn.close() 
    
    def get_all_products(self):
        """등록된 모든 제품 정보를 조회합니다."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT product_id, product_name, reg_date, last_update
                FROM product_table
                ORDER BY reg_date DESC
            """)
            
            # fetchall 결과를 딕셔너리 리스트로 변환
            columns = [column[0] for column in cursor.description]
            products = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            return products
            
        except sqlite3.Error as e:
            print(f"제품 목록 조회 중 오류 발생: {str(e)}")
            return []
            
        finally:
            conn.close()
    
    def get_all_equipments(self):
        """등록된 모든 장비 정보를 조회합니다."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT equipment_id, equipment_name, manager, reg_date, last_update
                FROM equipment_table
                ORDER BY reg_date DESC
            """)
            
            # fetchall 결과를 딕셔너리 리스트로 변환
            columns = [column[0] for column in cursor.description]
            equipments = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            return equipments
            
        except sqlite3.Error as e:
            print(f"장비 목록 조회 중 오류 발생: {str(e)}")
            return []
            
        finally:
            conn.close()
    
    def get_equipment_by_id(self, equipment_id):
        """장비 ID로 장비 정보 조회"""
        try:
            cursor = self.execute_query(
                "SELECT * FROM equipment_table WHERE equipment_id = ?",
                (equipment_id,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        except sqlite3.Error as e:
            self.db_error.emit(f"장비 정보 조회 실패: {str(e)}")
            return None
    
    def get_product_by_id(self, product_id):
        """제품 ID로 제품 정보 조회"""
        try:
            cursor = self.execute_query(
                "SELECT * FROM product_table WHERE product_id = ?",
                (product_id,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        except sqlite3.Error as e:
            self.db_error.emit(f"제품 정보 조회 실패: {str(e)}")
            return None
    
    def update_product_roi_settings(self, product_id, settings_json):
        """ROI 설정 업데이트"""
        try:
            self.execute_query('''
                UPDATE product_table 
                SET roi_settings = ?, last_update = datetime('now')
                WHERE product_id = ?
            ''', (settings_json, product_id))
            self.roi_settings_updated.emit(product_id)
            return True
        except Exception as e:
            self.db_error.emit(str(e))
            return False 