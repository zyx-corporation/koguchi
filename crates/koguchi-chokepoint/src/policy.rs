use std::path::{Path, PathBuf};

use crate::protocol::Result;

/// ALLOWED_OPERATIONS: v0.4 spike で許可する operation。
const ALLOWED_OPERATIONS: &[&str] = &["write_text", "read_text"];

/// workspace 内の安全な実パスを解決する。
/// .. による脱出や absolute path の workspace 外参照を拒否する。
pub fn resolve_target(workspace: &str, rel_path: &str) -> std::result::Result<PathBuf, String> {
    let ws = Path::new(workspace)
        .canonicalize()
        .map_err(|e| format!("cannot canonicalize workspace: {}", e))?;

    let candidate = ws.join(rel_path);

    // 存在する場合は canonicalize して workspace 配下か確認
    if candidate.exists() {
        let real = candidate
            .canonicalize()
            .map_err(|e| format!("cannot canonicalize path: {}", e))?;
        if !real.starts_with(&ws) {
            return Err("path escapes workspace".into());
        }
        return Ok(real);
    }

    // 存在しない場合は parent を canonicalize して確認
    if let Some(parent) = candidate.parent() {
        let real_parent = parent
            .canonicalize()
            .map_err(|e| format!("cannot canonicalize parent: {}", e))?;
        if !real_parent.starts_with(&ws) {
            return Err("path escapes workspace".into());
        }
    }

    Ok(candidate)
}

pub fn evaluate(req: &crate::protocol::Request) -> Result {
    if req.schema_version != crate::protocol::SCHEMA_VERSION {
        return Result::error(req.request_id.clone(), "unsupported schema_version");
    }

    if !ALLOWED_OPERATIONS.contains(&req.operation.as_str()) {
        return Result::denied(
            req.request_id.clone(),
            &format!("operation not allowed: {}", req.operation),
        );
    }

    match resolve_target(&req.workspace, &req.path) {
        Ok(resolved) => match req.operation.as_str() {
            "write_text" => {
                match std::fs::write(&resolved, &req.content) {
                    Ok(()) => Result::ok(req.request_id.clone(), "written".into()),
                    Err(e) => Result::error(req.request_id.clone(), &e.to_string()),
                }
            }
            "read_text" => {
                match std::fs::read_to_string(&resolved) {
                    Ok(data) => Result::ok(req.request_id.clone(), data),
                    Err(e) => Result::error(req.request_id.clone(), &e.to_string()),
                }
            }
            _ => Result::denied(
                req.request_id.clone(),
                &format!("unknown operation: {}", req.operation),
            ),
        },
        Err(reason) => Result::denied(req.request_id.clone(), &reason),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::protocol::Request;

    fn make_req(op: &str, ws: &str, path: &str) -> Request {
        Request {
            schema_version: 1,
            request_id: "test-1".into(),
            operation: op.into(),
            workspace: ws.into(),
            path: path.into(),
            content: "hello".into(),
        }
    }

    #[test]
    fn test_write_read_roundtrip() {
        let dir = tempfile::tempdir().unwrap();
        let ws = dir.path().to_str().unwrap();

        let req = make_req("write_text", ws, "out.txt");
        let result = evaluate(&req);
        assert!(result.allowed);
        assert_eq!(result.status, "ok");

        let req2 = make_req("read_text", ws, "out.txt");
        let result2 = evaluate(&req2);
        assert!(result2.allowed);
        assert_eq!(result2.stdout, "hello");
    }

    #[test]
    fn test_path_traversal_denied() {
        let dir = tempfile::tempdir().unwrap();
        let ws = dir.path().to_str().unwrap();
        let req = make_req("write_text", ws, "../evil.txt");
        let result = evaluate(&req);
        assert!(!result.allowed);
        assert!(result.error.unwrap().contains("escapes"));
    }

    #[test]
    fn test_unknown_operation_denied() {
        let dir = tempfile::tempdir().unwrap();
        let ws = dir.path().to_str().unwrap();
        let req = make_req("exec_shell", ws, "test");
        let result = evaluate(&req);
        assert!(!result.allowed);
    }

    #[test]
    fn test_request_id_conserved() {
        let dir = tempfile::tempdir().unwrap();
        let ws = dir.path().to_str().unwrap();
        let req = make_req("write_text", ws, "test.txt");
        let result = evaluate(&req);
        assert_eq!(result.request_id, "test-1");
    }

    #[test]
    fn test_schema_version_conserved() {
        let dir = tempfile::tempdir().unwrap();
        let ws = dir.path().to_str().unwrap();
        let req = make_req("write_text", ws, "test.txt");
        let result = evaluate(&req);
        assert_eq!(result.schema_version, 1);
    }
}
