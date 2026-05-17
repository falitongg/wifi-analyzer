"""
Centralized WLAN interface manager for MicroPython (Raspberry Pi Pico W).

Owns the single network.WLAN object and serializes all radio operations
through an internal FIFO queue so that scan and connect can never run
simultaneously on the same hardware.

Consumers (WiFiScanner, MQTTManager) must never create their own
network.WLAN instances; they receive this manager via dependency injection
and call request_scan() / request_connect() instead.

Call process() on every main-loop iteration to drain the queue.
"""

import network
import time
import config


class WLANManager:
    """
    Single owner of the WLAN STA interface.

    Operations are represented as integer op-codes stored in a list that
    acts as a FIFO queue.  process() pops the head entry and executes it
    to completion before returning, so the caller's loop naturally
    serialises all radio activity.

    Scan operations block for ~2-4 s (MicroPython wlan.scan() is
    inherently synchronous). Connect operations return quickly; firmware
    handles the actual association asynchronously and the result is
    polled via is_connected().
    """

    # Operation codes used in the internal queue
    _OP_SCAN    = 0
    _OP_CONNECT = 1

    # Minimum time between consecutive connect() calls (ms)
    _CONNECT_COOLDOWN_MS = 10_000

    def __init__(self):
        # The one and only WLAN object in the entire firmware image
        self._wlan = network.WLAN(network.STA_IF)
        self._wlan.active(True)

        # FIFO queue; each entry is a (op_code, callback | None) tuple
        self._queue = []

        # Re-entry guard: True while a _run_* method is on the call stack
        self._executing = False

        # ticks_ms() at the last wlan.connect() call; 0 means never
        self._last_connect_ms = 0

    # ------------------------------------------------------------------
    # Public status helpers
    # These are plain reads and are safe to call at any time.
    # ------------------------------------------------------------------

    def is_connected(self):
        """Return True when the interface holds a valid DHCP/IP address."""
        # status 3 == network.STAT_GOT_IP on Pico W
        return self._wlan.status() == 3

    def raw_status(self):
        """
        Return the raw wlan.status() integer.
        Useful for diagnostic log messages.
        """
        return self._wlan.status()

    # ------------------------------------------------------------------
    # Queue API
    # ------------------------------------------------------------------

    def request_scan(self, on_done=None):
        """
        Enqueue a Wi-Fi scan.

        Duplicate requests are silently dropped so the queue never holds
        more than one pending scan at a time.

        Parameters
        ----------
        on_done : callable(list) | None
            Invoked with the result list when the scan finishes.
            Each list element is a dict: {'ssid': str, 'rssi': int, 'channel': int}.
        """
        for op, _ in self._queue:
            if op == self._OP_SCAN:
                return  # already queued; discard duplicate
        self._queue.append((self._OP_SCAN, on_done))

    def request_connect(self, on_done=None):
        """
        Enqueue a Wi-Fi connection attempt.

        If the interface is already connected the callback is fired
        immediately with True and nothing is added to the queue.
        Duplicate requests are silently dropped.

        Parameters
        ----------
        on_done : callable(bool) | None
            Invoked with True if already connected, or False once the
            connect trigger has been sent.  Because association is
            asynchronous, poll is_connected() to know when it succeeds.
        """
        if self.is_connected():
            if on_done:
                on_done(True)
            return
        for op, _ in self._queue:
            if op == self._OP_CONNECT:
                return  # already queued; discard duplicate
        self._queue.append((self._OP_CONNECT, on_done))

    def process(self):
        """
        Pop and execute the next queued operation, then return.

        Must be called once per main-loop iteration.  The guard flag
        _executing prevents any re-entrant call (e.g. from a callback)
        from corrupting the queue mid-execution.
        """
        if self._executing or not self._queue:
            return

        op, callback = self._queue.pop(0)
        self._executing = True

        try:
            if op == self._OP_SCAN:
                result = self._run_scan()
            elif op == self._OP_CONNECT:
                result = self._run_connect()
            else:
                result = None

            if callback is not None:
                callback(result)
        finally:
            # Always clear the guard, even if the callback raised
            self._executing = False

    # ------------------------------------------------------------------
    # Private operation implementations
    # ------------------------------------------------------------------

    def _run_scan(self):
        """
        Perform a blocking Wi-Fi scan and return parsed results.

        Returns
        -------
        list of dict
            Keys: 'ssid' (str), 'rssi' (int dBm), 'channel' (int).
            Networks with undecodable or empty SSIDs are skipped.
        """
        raw = self._wlan.scan()
        results = []

        for net in raw:
            try:
                ssid = net[0].decode('utf-8')
                if not ssid:
                    continue
                results.append({
                    'ssid':    ssid,
                    'rssi':    net[3],
                    'channel': net[2],
                })
            except UnicodeError:
                pass  # skip networks with non-UTF-8 SSIDs

        return results

    def _run_connect(self):
        """
        Trigger a Wi-Fi connection attempt, guarded by a cooldown.

        Skips the call if:
          - the interface is already connected, or
          - firmware is still in the association handshake (status 1), or
          - fewer than _CONNECT_COOLDOWN_MS ms have elapsed since the
            last trigger.

        Returns
        -------
        bool
            Always False; the caller must poll is_connected() separately.
        """
        if self.is_connected():
            return True

        status = self._wlan.status()

        # status 1 == network.STAT_CONNECTING: firmware is busy; wait
        if status == 1:
            return False

        now = time.ticks_ms()
        if self._last_connect_ms != 0 and \
                time.ticks_diff(now, self._last_connect_ms) < self._CONNECT_COOLDOWN_MS:
            return False  # still inside the cooldown window

        print(f"[WLAN] Connecting... status={status}")
        self._wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
        self._last_connect_ms = now
        return False  # association happens asynchronously