CREATE TABLE IF NOT EXISTS scans (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT    NOT NULL,
    data      TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_scans_ts ON scans (timestamp DESC);
