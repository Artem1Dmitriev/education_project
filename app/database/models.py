
from sqlalchemy import (
Column ,String ,DateTime ,Boolean ,Integer ,Numeric ,Text ,
ForeignKey ,BigInteger ,CheckConstraint ,UniqueConstraint ,Index ,
Date ,Time ,MetaData ,func ,event ,Sequence ,PrimaryKeyConstraint 
)
from sqlalchemy .dialects .postgresql import UUID ,INET ,JSONB 
from sqlalchemy .orm import relationship ,validates 
from sqlalchemy .sql import expression ,text 
from datetime import datetime ,date 
import uuid 
from app .database .session import Base 


class User (Base ):
    """Пользователи системы"""
    __tablename__ ='users'
    __table_args__ =(
    CheckConstraint ("email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$'",name ='chk_email_format'),
    CheckConstraint ('current_daily_usage <= daily_limit',name ='chk_daily_usage'),
    CheckConstraint ('current_monthly_usage <= monthly_limit',name ='chk_monthly_usage'),
    {'schema':'ai_framework'}
    )

    user_id =Column (UUID (as_uuid =True ),primary_key =True ,default =uuid .uuid4 )
    username =Column (String (50 ),unique =True ,nullable =False )
    email =Column (String (100 ),unique =True ,nullable =False )
    api_key_hash =Column (String (64 ))
    daily_limit =Column (Numeric (12 ,2 ),default =100.00 )
    current_daily_usage =Column (Numeric (12 ,2 ),default =0 )
    monthly_limit =Column (Numeric (12 ,2 ),default =1000.00 )
    current_monthly_usage =Column (Numeric (12 ,2 ),default =0 )
    is_active =Column (Boolean ,default =True )
    created_at =Column (DateTime (timezone =True ),default =func .now ())
    updated_at =Column (DateTime (timezone =True ),default =func .now (),onupdate =func .now ())

    requests =relationship ("Request",back_populates ="user")
    files =relationship ("File",back_populates ="user")
    error_logs =relationship ("ErrorLog",back_populates ="user")
    usage_statistics =relationship ("UsageStatistics",back_populates ="user")

    def __repr__ (self ):
        return f"<User {self .username } ({self .email })>"


class Provider (Base ):
    """AI-провайдеры"""
    __tablename__ ='providers'
    __table_args__ =(
    CheckConstraint ("auth_type IN ('Bearer', 'X-API-Key', 'APIKey', 'Custom')",name ='chk_auth_type'),
    {'schema':'ai_framework'}
    )

    provider_id =Column (UUID (as_uuid =True ),primary_key =True ,default =uuid .uuid4 )
    provider_name =Column (String (50 ),unique =True ,nullable =False )
    base_url =Column (String (255 ),nullable =False )
    auth_type =Column (String (20 ),nullable =False )
    max_requests_per_minute =Column (Integer ,default =60 )
    retry_count =Column (Integer ,default =3 )
    timeout_seconds =Column (Integer ,default =30 )
    is_active =Column (Boolean ,default =True )
    created_at =Column (DateTime (timezone =True ),default =func .now ())

    ai_models =relationship ("AIModel",back_populates ="provider")
    api_keys =relationship ("APIKey",back_populates ="provider")
    error_logs =relationship ("ErrorLog",back_populates ="provider")
    usage_statistics =relationship ("UsageStatistics",back_populates ="provider")

    def __repr__ (self ):
        return f"<Provider {self .provider_name }>"


class AIModel (Base ):
    """Модели нейросетей"""
    __tablename__ ='ai_models'
    __table_args__ =(
    CheckConstraint ('context_window > 0',name ='chk_context_window'),
    CheckConstraint ('input_price_per_1k >= 0',name ='chk_input_price'),
    CheckConstraint ('output_price_per_1k >= 0',name ='chk_output_price'),
    CheckConstraint ('priority BETWEEN 1 AND 10',name ='chk_priority'),
    CheckConstraint ("model_type IN ('text', 'vision', 'audio', 'multimodal')",name ='chk_model_type'),
    UniqueConstraint ('provider_id','model_name',name ='uq_provider_model'),
    {'schema':'ai_framework'}
    )

    model_id =Column (UUID (as_uuid =True ),primary_key =True ,default =uuid .uuid4 )
    provider_id =Column (UUID (as_uuid =True ),ForeignKey ('ai_framework.providers.provider_id',ondelete ='CASCADE'),
    nullable =False )
    model_name =Column (String (100 ),nullable =False )
    model_type =Column (String (20 ),default ='text')
    context_window =Column (Integer ,nullable =False )
    max_output_tokens =Column (Integer )
    supports_json_mode =Column (Boolean ,default =False )
    supports_function_calling =Column (Boolean ,default =False )
    input_price_per_1k =Column (Numeric (10 ,6 ),nullable =False )
    output_price_per_1k =Column (Numeric (10 ,6 ),nullable =False )
    is_available =Column (Boolean ,default =True )
    priority =Column (Integer ,default =5 )
    created_at =Column (DateTime (timezone =True ),default =func .now ())
    updated_at =Column (DateTime (timezone =True ),default =func .now (),onupdate =func .now ())

    provider =relationship ("Provider",back_populates ="ai_models")
    requests =relationship ("Request",back_populates ="model")

    def __repr__ (self ):
        return f"<AIModel {self .model_name } ({self .provider .provider_name })>"


class APIKey (Base ):
    """API-ключи провайдеров"""
    __tablename__ ='api_keys'
    __table_args__ =(
    CheckConstraint ('current_usage_usd >= 0',name ='chk_current_usage'),
    CheckConstraint ('current_usage_usd <= usage_limit_usd OR usage_limit_usd IS NULL',name ='chk_usage_limit'),
    {'schema':'ai_framework'}
    )

    key_id =Column (UUID (as_uuid =True ),primary_key =True ,default =uuid .uuid4 )
    provider_id =Column (UUID (as_uuid =True ),ForeignKey ('ai_framework.providers.provider_id',ondelete ='CASCADE'),
    nullable =False )
    api_key_encrypted =Column (Text ,nullable =False )
    key_description =Column (String (255 ))
    usage_limit_usd =Column (Numeric (12 ,2 ))
    current_usage_usd =Column (Numeric (12 ,2 ),default =0 )
    rate_limit_per_minute =Column (Integer ,default =60 )
    requests_count =Column (Integer ,default =0 )
    last_used =Column (DateTime (timezone =True ))
    is_active =Column (Boolean ,default =True )
    is_primary =Column (Boolean ,default =False )
    created_at =Column (DateTime (timezone =True ),default =func .now ())

    provider =relationship ("Provider",back_populates ="api_keys")
    requests =relationship ("Request",back_populates ="api_key")

    def __repr__ (self ):
        return f"<APIKey {self .key_id [:8 ]}... ({self .provider .provider_name })>"


class Request (Base ):
    """Запросы к нейросетям"""
    __tablename__ ='requests'
    __table_args__ =(
    CheckConstraint ('input_tokens >= 0',name ='chk_input_tokens'),
    CheckConstraint ('output_tokens >= 0',name ='chk_output_tokens'),
    CheckConstraint ('total_cost >= 0',name ='chk_total_cost'),
    CheckConstraint ('temperature BETWEEN 0 AND 2',name ='chk_temperature'),
    CheckConstraint ('top_p BETWEEN 0 AND 1',name ='chk_top_p'),
    CheckConstraint ('frequency_penalty BETWEEN -2 AND 2',name ='chk_frequency_penalty'),
    CheckConstraint ('presence_penalty BETWEEN -2 AND 2',name ='chk_presence_penalty'),
    CheckConstraint ('processing_time_ms >= 0',name ='chk_processing_time'),
    CheckConstraint ("status IN ('pending', 'processing', 'completed', 'failed', 'cached')",name ='chk_status'),
    {'schema':'ai_framework'}
    )

    request_id =Column (UUID (as_uuid =True ),primary_key =True ,default =uuid .uuid4 )
    user_id =Column (UUID (as_uuid =True ),ForeignKey ('ai_framework.users.user_id',ondelete ='SET NULL'))
    model_id =Column (UUID (as_uuid =True ),ForeignKey ('ai_framework.ai_models.model_id',ondelete ='RESTRICT'),
    nullable =False )
    api_key_id =Column (UUID (as_uuid =True ),ForeignKey ('ai_framework.api_keys.key_id',ondelete ='SET NULL'))
    prompt_hash =Column (String (64 ),nullable =False )
    input_text =Column (Text )
    input_tokens =Column (Integer )
    output_tokens =Column (Integer )
    total_cost =Column (Numeric (10 ,6 ))
    temperature =Column (Numeric (3 ,2 ),default =0.7 )
    max_tokens =Column (Integer )
    top_p =Column (Numeric (3 ,2 ),default =1.0 )
    frequency_penalty =Column (Numeric (3 ,2 ),default =0 )
    presence_penalty =Column (Numeric (3 ,2 ),default =0 )
    status =Column (String (20 ),default ='pending')
    request_timestamp =Column (DateTime (timezone =True ),default =func .now ())
    processing_time_ms =Column (Integer )
    client_ip =Column (INET )
    user_agent =Column (Text )
    endpoint_called =Column (String (255 ))

    user =relationship ("User",back_populates ="requests")
    model =relationship ("AIModel",back_populates ="requests")
    api_key =relationship ("APIKey",back_populates ="requests")
    files =relationship ("File",back_populates ="request")
    response =relationship ("Response",back_populates ="request",uselist =False )
    error_logs =relationship ("ErrorLog",back_populates ="request")

    def __repr__ (self ):
        return f"<Request {self .request_id [:8 ]}... ({self .status })>"


class File (Base ):
    """Файлы, загруженные пользователями"""
    __tablename__ ='files'
    __table_args__ =(
    CheckConstraint ('file_size_bytes > 0',name ='chk_file_size'),
    CheckConstraint ("processing_status IN ('uploaded', 'processing', 'processed', 'failed')",
    name ='chk_processing_status'),
    {'schema':'ai_framework'}
    )

    file_id =Column (UUID (as_uuid =True ),primary_key =True ,default =uuid .uuid4 )
    request_id =Column (UUID (as_uuid =True ),ForeignKey ('ai_framework.requests.request_id',ondelete ='CASCADE'))
    user_id =Column (UUID (as_uuid =True ),ForeignKey ('ai_framework.users.user_id',ondelete ='CASCADE'))
    file_name =Column (String (255 ),nullable =False )
    file_size_bytes =Column (Integer )
    file_type =Column (String (50 ),nullable =False )
    mime_type =Column (String (100 ))
    storage_path =Column (Text ,nullable =False )
    processing_status =Column (String (20 ),default ='uploaded')
    extracted_text =Column (Text )
    ocr_used =Column (Boolean ,default =False )
    uploaded_at =Column (DateTime (timezone =True ),default =func .now ())
    processed_at =Column (DateTime (timezone =True ))

    request =relationship ("Request",back_populates ="files")
    user =relationship ("User",back_populates ="files")

    def __repr__ (self ):
        return f"<File {self .file_name } ({self .file_type })>"


class Response (Base ):
    """Ответы от нейросетей"""
    __tablename__ ='responses'
    __table_args__ ={'schema':'ai_framework'}

    response_id =Column (UUID (as_uuid =True ),primary_key =True ,default =uuid .uuid4 )
    request_id =Column (UUID (as_uuid =True ),ForeignKey ('ai_framework.requests.request_id',ondelete ='CASCADE'),
    unique =True ,nullable =False )
    content =Column (Text ,nullable =False )
    summary =Column (Text )
    finish_reason =Column (String (50 ))
    model_used =Column (String (100 ))
    provider_used =Column (String (50 ))
    response_timestamp =Column (DateTime (timezone =True ),default =func .now ())
    is_cached =Column (Boolean ,default =False )
    embedding_vector =Column (Text )

    request =relationship ("Request",back_populates ="response")
    cache =relationship ("Cache",back_populates ="response",uselist =False )

    def __repr__ (self ):
        return f"<Response for {self .request_id [:8 ]}...>"


class Cache (Base ):
    """Кеш для семантического поиска"""
    __tablename__ ='cache'
    __table_args__ =(
    CheckConstraint ('similarity_score BETWEEN 0 AND 1',name ='chk_similarity_score'),
    {'schema':'ai_framework'}
    )

    cache_id =Column (UUID (as_uuid =True ),primary_key =True ,default =uuid .uuid4 )
    request_hash =Column (String (64 ),unique =True ,nullable =False )
    response_id =Column (UUID (as_uuid =True ),ForeignKey ('ai_framework.responses.response_id',ondelete ='CASCADE'),
    nullable =False )
    embedding_hash =Column (String (64 ))
    similarity_score =Column (Numeric (5 ,4 ))
    created_at =Column (DateTime (timezone =True ),default =func .now ())
    expires_at =Column (DateTime (timezone =True ))
    last_accessed =Column (DateTime (timezone =True ),default =func .now ())
    access_count =Column (Integer ,default =1 )
    ttl_days =Column (Integer ,default =30 )

    response =relationship ("Response",back_populates ="cache")

    def __repr__ (self ):
        return f"<Cache {self .request_hash [:8 ]}...>"


class ErrorLog (Base ):
    """Логи ошибок"""
    __tablename__ ='error_logs'
    __table_args__ ={'schema':'ai_framework'}

    error_id =Column (UUID (as_uuid =True ),primary_key =True ,default =uuid .uuid4 )
    request_id =Column (UUID (as_uuid =True ),ForeignKey ('ai_framework.requests.request_id',ondelete ='SET NULL'))
    user_id =Column (UUID (as_uuid =True ),ForeignKey ('ai_framework.users.user_id',ondelete ='SET NULL'))
    provider_id =Column (UUID (as_uuid =True ),ForeignKey ('ai_framework.providers.provider_id',ondelete ='SET NULL'))
    error_type =Column (String (50 ),nullable =False )
    error_code =Column (String (50 ))
    error_message =Column (Text ,nullable =False )
    http_status_code =Column (Integer )
    retry_attempt =Column (Integer ,default =0 )
    fallback_used =Column (Boolean ,default =False )
    fallback_to_model =Column (String (100 ))
    timestamp =Column (DateTime (timezone =True ),default =func .now ())
    resolved_at =Column (DateTime (timezone =True ))

    request =relationship ("Request",back_populates ="error_logs")
    user =relationship ("User",back_populates ="error_logs")
    provider =relationship ("Provider",back_populates ="error_logs")

    def __repr__ (self ):
        return f"<ErrorLog {self .error_type }>"


class UsageStatistics (Base ):
    """Статистика использования"""
    __tablename__ ='usage_statistics'
    __table_args__ =(
    CheckConstraint ("period_type IN ('hourly', 'daily', 'weekly', 'monthly')",name ='chk_period_type'),
    UniqueConstraint ('user_id','provider_id','model_name','period_type','period_start',name ='uq_stats'),
    {'schema':'ai_framework'}
    )

    stat_id =Column (UUID (as_uuid =True ),primary_key =True ,default =uuid .uuid4 )
    period_type =Column (String (10 ),nullable =False )
    period_start =Column (DateTime (timezone =True ),nullable =False )
    period_end =Column (DateTime (timezone =True ),nullable =False )
    user_id =Column (UUID (as_uuid =True ),ForeignKey ('ai_framework.users.user_id',ondelete ='CASCADE'))
    total_requests =Column (Integer ,default =0 )
    successful_requests =Column (Integer ,default =0 )
    failed_requests =Column (Integer ,default =0 )
    total_input_tokens =Column (BigInteger ,default =0 )
    total_output_tokens =Column (BigInteger ,default =0 )
    total_cost =Column (Numeric (12 ,6 ),default =0 )
    provider_id =Column (UUID (as_uuid =True ),ForeignKey ('ai_framework.providers.provider_id',ondelete ='CASCADE'))
    model_name =Column (String (100 ))
    requests_per_provider =Column (Integer ,default =0 )
    avg_response_time_ms =Column (Integer )
    cache_hits =Column (Integer ,default =0 )
    cache_misses =Column (Integer ,default =0 )

    user =relationship ("User",back_populates ="usage_statistics")
    provider =relationship ("Provider",back_populates ="usage_statistics")

    def __repr__ (self ):
        return f"<UsageStatistics {self .period_type } {self .period_start }>"


class SystemSetting (Base ):
    """Системные настройки"""
    __tablename__ ='system_settings'
    __table_args__ =(
    CheckConstraint ("setting_type IN ('string', 'integer', 'float', 'boolean', 'json')",name ='chk_setting_type'),
    {'schema':'ai_framework'}
    )

    setting_id =Column (UUID (as_uuid =True ),primary_key =True ,default =uuid .uuid4 )
    setting_key =Column (String (100 ),unique =True ,nullable =False )
    setting_value =Column (Text )
    setting_type =Column (String (20 ),default ='string')
    category =Column (String (50 ),default ='general')
    description =Column (Text )
    is_encrypted =Column (Boolean ,default =False )
    updated_at =Column (DateTime (timezone =True ),default =func .now (),onupdate =func .now ())
    updated_by =Column (UUID (as_uuid =True ),ForeignKey ('ai_framework.users.user_id',ondelete ='SET NULL'))

    def __repr__ (self ):
        return f"<SystemSetting {self .setting_key }>"


def get_model_by_table_name (table_name :str ):
    """Получить класс модели по названию таблицы"""
    models ={
    "users":User ,
    "providers":Provider ,
    "ai_models":AIModel ,
    "api_keys":APIKey ,
    "requests":Request ,
    "files":File ,
    "responses":Response ,
    "cache":Cache ,
    "error_logs":ErrorLog ,
    "usage_statistics":UsageStatistics ,
    "system_settings":SystemSetting ,
    }
    return models .get (table_name )