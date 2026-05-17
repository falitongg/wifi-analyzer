"""
Wi-Fi network scanner.

Delegates all radio operations to the shared WLANManager so that no
second WLAN object is ever created.  Tracks network appearance and
disappearance across consecutive scans to drive the indicator LEDs.
"""

import indicators


class WiFiScanner:
    """
    Thin wrapper around WLANManager.request_scan() that adds
    new/lost-network detection for LED feedback.

    Parameters
    ----------
    wlan_manager : WLANManager
        The single shared radio manager; injected by main.py.
    on_data_ready : callable(list) | None
        Optional callback invoked after each completed scan, after
        indicator logic has run.  main.py uses this to update wifi_data
        and trigger MQTT publishing.
    """

    def __init__(self, wlan_manager, on_data_ready=None):
        self._wm            = wlan_manager
        self._on_data_ready = on_data_ready

        self._previous_ssids = set()
        self._latest_results = []  # cached output of the most recent scan

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def request_scan(self):
        """
        Queue a scan through WLANManager.

        Returns immediately; the result arrives asynchronously via
        _on_scan_done() once WLANManager.process() executes the op.
        Use get_results() to read the latest completed scan at any time.
        """
        self._wm.request_scan(on_done=self._on_scan_done)

    def get_results(self):
        """
        Return the most recent completed scan results.

        Returns
        -------
        list of dict
            Format: [{'ssid': str, 'rssi': int, 'channel': int}, ...]
            Empty list until the first scan completes.
        """
        return self._latest_results

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _on_scan_done(self, results):
        """
        Callback wired to WLANManager; called when a scan finishes.

        Compares current SSIDs with the previous set to detect changes,
        fires the appropriate indicator, caches the results, then
        forwards to the external on_data_ready callback if supplied.
        """
        current_ssids = {net['ssid'] for net in results}

        new_networks  = current_ssids - self._previous_ssids
        lost_networks = self._previous_ssids - current_ssids

        if new_networks:
            indicators.network_status(True)   # green blink
        if lost_networks:
            indicators.network_status(False)  # red blink

        self._previous_ssids = current_ssids
        self._latest_results = results

        if self._on_data_ready is not None:
            self._on_data_ready(results)