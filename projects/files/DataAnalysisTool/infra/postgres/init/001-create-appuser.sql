CREATE USER appuser WITH PASSWORD 'apppassword';

CREATE DATABASE dataanalysis OWNER appuser;

GRANT ALL PRIVILEGES ON DATABASE dataanalysis TO appuser;
