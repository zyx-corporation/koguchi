use serde::{Deserialize, Serialize};

pub const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Deserialize)]
pub struct Request {
    pub schema_version: u32,
    pub request_id: String,
    pub operation: String,
    pub workspace: String,
    pub path: String,
    #[serde(default)]
    pub content: String,
}

#[derive(Debug, Serialize)]
pub struct Result {
    pub schema_version: u32,
    pub request_id: String,
    pub allowed: bool,
    pub status: String,
    pub exit_code: Option<i32>,
    pub stdout: String,
    pub stderr: String,
    pub error: Option<String>,
}

impl Result {
    pub fn ok(request_id: String, stdout: String) -> Self {
        Result {
            schema_version: SCHEMA_VERSION,
            request_id,
            allowed: true,
            status: "ok".into(),
            exit_code: Some(0),
            stdout,
            stderr: String::new(),
            error: None,
        }
    }

    pub fn denied(request_id: String, reason: &str) -> Self {
        Result {
            schema_version: SCHEMA_VERSION,
            request_id,
            allowed: false,
            status: "denied".into(),
            exit_code: None,
            stdout: String::new(),
            stderr: String::new(),
            error: Some(reason.into()),
        }
    }

    pub fn error(request_id: String, message: &str) -> Self {
        Result {
            schema_version: SCHEMA_VERSION,
            request_id,
            allowed: false,
            status: "error".into(),
            exit_code: None,
            stdout: String::new(),
            stderr: String::new(),
            error: Some(message.into()),
        }
    }
}
