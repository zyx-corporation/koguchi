mod protocol;
mod policy;

use std::io::{self, Read};

fn main() {
    let mut input = String::new();
    io::stdin().read_to_string(&mut input).unwrap();

    let result = match serde_json::from_str::<protocol::Request>(&input) {
        Ok(req) => policy::evaluate(&req),
        Err(e) => protocol::Result::error(
            "unknown".into(),
            &format!("invalid JSON request: {}", e),
        ),
    };

    let output = serde_json::to_string(&result).unwrap();
    println!("{}", output);
}
