import dbus
import dbus.mainloop.glib
import dbus.service
import os
import subprocess
import time

from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

DBusGMainLoop(set_as_default=True)

from libraries.bluetooth import constants
from libraries.bluetooth.agent import Agent
from Utils.utils import run


class BluetoothDeviceManager:
    """A class for managing Bluetooth devices using the BlueZ D-Bus API."""

    def __init__(self, log=None, interface=None):
        """Initialize the BluetoothDeviceManager by setting up the system bus and adapter.

        Args:
            log: Logger instance.
            interface: Bluetooth adapter interface (e.g., hci0).
        """
        self.agent = None
        self.bus = dbus.SystemBus()
        self.interface = interface
        self.log = log
        self.adapter_path = f'{constants.bluez_path}/{self.interface}'
        self.adapter_proxy = self.bus.get_object(constants.bluez_service, self.adapter_path)
        self.adapter = dbus.Interface(self.adapter_proxy, constants.adapter_interface)
        self.adapter_properties = dbus.Interface(self.adapter_proxy, constants.properties_interface)
        self.object_manager = dbus.Interface(self.bus.get_object(constants.bluez_service, "/"), constants.object_manager_interface)
        self.opp_process = None
        self.pulseaudio_process = None
        self.stream_process = None

    def get_paired_devices(self):
        """Retrieves all Bluetooth devices that are currently paired with the adapter.

        Returns:
            paired_devices: A dictionary of paired devices.
        """
        paired_devices = {}
        for path, interfaces in self.object_manager.GetManagedObjects().items():
            if constants.device_interface in interfaces:
                device = interfaces[constants.device_interface]
                if device.get("Paired") and device.get("Adapter") == self.adapter_path:
                    address = device.get("Address")
                    name = device.get("Name", "Unknown")
                    paired_devices[address] = name
        return paired_devices

    def start_discovery(self):
        """Start scanning for nearby Bluetooth devices, if not already discovering."""
        try:
            if not self.adapter_properties.Get(constants.adapter_interface, "Discovering"):
                self.adapter.StartDiscovery()
                self.log.info("Discovery started.")
            else:
                self.log.info("Discovery already in progress.")
        except dbus.exceptions.DBusException as error:
            self.log.error("Failed to start discovery: %s", error)

    def stop_discovery(self):
        """Stop Bluetooth device discovery, if it's running."""
        try:
            if self.adapter_properties.Get(constants.adapter_interface, "Discovering"):
                self.adapter.StopDiscovery()
                self.log.info("Discovery stopped.")
            else:
                self.log.info("Discovery is not running.")
        except dbus.exceptions.DBusException as error:
            self.log.error("Failed to stop discovery: %s", error)

    def get_discovered_devices(self):
        """Retrieve discovered Bluetooth devices under the current adapter.

        Returns:
            discovered_devices: List of discovered Bluetooth devices.
        """
        discovered_devices = []
        for path, interfaces in self.object_manager.GetManagedObjects().items():
            device = interfaces.get(constants.device_interface)
            if not device or device.get("Adapter") != self.adapter_path:
                continue
            address = device.get("Address")
            alias = device.get("Alias", "Unknown")
            if address:
                discovered_devices.append({
                    "path": path,
                    "address": address,
                    "alias": alias})
            else:
                self.log.warning("Failed to extract device info from %s", path)
        return discovered_devices

    def get_device_path(self, device_address):
        """Constructs the D-Bus Object path for a bluetooth device using its address.

        Args:
            device_address: Bluetooth address of the remote device.

        Returns:
            device_path: D-Bus Object path
        """
        formatted_address=device_address.replace(":", "_")
        device_path=f"{constants.bluez_path}/{self.interface}/dev_{formatted_address}"
        return device_path


    def setup_agent(self, ui_callback):
        """Ensures the Bluetooth agent object is created and ready."""
        self.agent = Agent(self.bus, constants.agent_path, ui_callback, self.log)

    def register_agent(self, capability=None, ui_callback=None):
        """Register the Bluetooth agent with BlueZ to handle pairing requests."""
        try:
            if self.agent is None:
                self.setup_agent(ui_callback)
            agent_manager = dbus.Interface(self.bus.get_object(constants.bluez_service, constants.bluez_path), constants.agent_interface)
            agent_manager.RegisterAgent(constants.agent_path, capability)
            agent_manager.RequestDefaultAgent(constants.agent_path)
            self.log.info("Registered Agent successfully at %s with capability: %s", constants.agent_path, capability)
            return True
        except dbus.exceptions.DBusException as error:
            self.log.error("Failed to register agent: %s", error)
            return False

    def unregister_agent(self):
        """Unregister the Bluetooth agent from BlueZ."""
        try:
            agent_manager = dbus.Interface(self.bus.get_object(constants.bluez_service, constants.bluez_path), constants.agent_interface)
            agent_manager.UnregisterAgent(constants.agent_path)
            self.log.info("Unregistered agent from BlueZ.")
        except dbus.exceptions.DBusException as error:
            self.log.error("Failed to unregister agent: %s", error)

    def pair(self, address):
        """Pairs with a Bluetooth device using the given controller interface.

        Args:
            address: Bluetooth address of remote device.

        Returns:
            True if successfully paired, False otherwise.
        """
        device_path = self.get_device_path(address)
        try:
            device_proxy = self.bus.get_object(constants.bluez_service, device_path)
            device = dbus.Interface(device_proxy, constants.device_interface)
            properties = dbus.Interface(device_proxy, constants.properties_interface)
            paired = properties.Get(constants.device_interface, "Paired")
            if paired:
                self.log.info("Device %s is already paired.", address)
                return True
            self.log.info("Initiating pairing with %s", address)
            device.Pair()
            paired = properties.Get(constants.device_interface, "Paired")
            if paired:
                self.log.info("Successfully paired with %s", address)
                return True
        except dbus.exceptions.DBusException as error:
            if "NoReply" in error.get_dbus_name():
                self.log.info("Pair() timed out for %s, ignoring as pairing may still succeed.", address)
            else:
                self.log.error("Pairing failed with %s: %s", address, str(error))
                return False

    def connect(self, address):
        """Establish a  connection to the specified Bluetooth device.

        Args:
            address: Bluetooth device address of remote device.

        Returns:
            True if connected, False otherwise.
        """
        device_path = self.get_device_path(address)
        try:
            device = dbus.Interface(self.bus.get_object(constants.bluez_service, device_path), constants.device_interface)
            device.Connect()
            properties = dbus.Interface(self.bus.get_object(constants.bluez_service, device_path), constants.properties_interface)
            connected = properties.Get(constants.device_interface, "Connected")
            if connected:
                self.log.info("Connection successful to %s", address)
                return True
        except Exception as error:
            self.log.info("Connection failed:%s", error)
            return False

    def disconnect(self, address):
        """Disconnect a Bluetooth  device from the specified adapter.

        Args:
            address: Bluetooth  address of the remote device.

        Returns:
            True if disconnected or already disconnected, False if an error occurred.
        """
        device_path = self.get_device_path(address)
        try:
            device = dbus.Interface(self.bus.get_object(constants.bluez_service, device_path), constants.device_interface)
            properties = dbus.Interface(self.bus.get_object(constants.bluez_service, device_path), constants.properties_interface)
            connected = properties.Get(constants.device_interface, "Connected")
            if not connected:
                self.log.info("Device %s is already disconnected.", address)
                return True
            device.Disconnect()
            return True
        except dbus.exceptions.DBusException as error:
            self.log.info("Error disconnecting device %s:%s", address, error)
            return False

    def unpair_device(self, address):
        """Unpairs a paired or known Bluetooth device from the system using BlueZ D-Bus.

        Args:
            address: The Bluetooth address of the remote device.

        Returns:
            True if the device was unpaired successfully or already not present,
            False if the unpairing failed or the device still exists afterward.
        """
        try:
            target_path = None
            for path, interfaces in self.object_manager.GetManagedObjects().items():
                if constants.device_interface in interfaces and interfaces[constants.device_interface].get("Address") == address and path.startswith(self.adapter_path):
                    target_path = path
                    break
            if not target_path:
                self.log.info("Device with address %s not found on %s", address, self.interface)
                return True
            self.adapter.RemoveDevice(target_path)
            self.log.info("Requested unpair of device %s at path %s", address, target_path)
            time.sleep(0.5)
            for path, interfaces in self.object_manager.GetManagedObjects().items():
                if constants.device_interface in interfaces and interfaces[constants.device_interface].get("Address") == address:
                        self.log.warning("Device %s still exists after attempted unpair", address)
                        return False
            self.log.info("Device %s unpaired successfully", address)
            return True
        except dbus.exceptions.DBusException as error:
            self.log.error("DBusException while unpairing device %s: %s", address, str(error))
            return False

    def is_device_paired(self, device_address):
        """Checks if the specified device is paired.

        Args:
            device_address: Bluetooth address of remote device.

        Returns:
            True if paired, False otherwise.
        """
        device_path = self.get_device_path(device_address)
        properties = dbus.Interface(self.bus.get_object(constants.bluez_service, device_path), constants.properties_interface)
        try:
            return properties.Get(constants.device_interface, "Paired")
        except dbus.exceptions.DBusException as error:
            self.log.debug("DBusException while checking pairing:%s", str(error))
            return False

    def is_device_connected(self, device_address):
        """Checks if the specified device is connected.

        Args:
            device_address: Bluetooth address of remote device.

        Returns:
            True if connected, False otherwise.
        """
        device_path = self.get_device_path(device_address)
        if not device_path:
            self.log.debug("Device path not found for %s on %s", device_address, self.interface)
            return False
        try:
            properties = dbus.Interface(self.bus.get_object(constants.bluez_service, device_path), constants.properties_interface)
            connected = properties.Get(constants.device_interface, "Connected")
            return connected
        except dbus.exceptions.DBusException as error:
            self.log.debug("D-BusException while checking connection:%s", str(error))
            return False

    def start_a2dp_stream(self, address, filepath=None):
        """Initiates an A2DP audio stream to a Bluetooth device using PulseAudio.

        Args:
            address: Bluetooth address of remote device.
            filepath: Path to the audio file.

        Returns:
            True if the stream was started, False otherwise.
        """
        device_path = self.find_device_path(address)
        self.log.info("Device path: %s", device_path)
        if not device_path:
            return None
        try:
            if not filepath or not os.path.exists(filepath):
                self.log.warning("File path %s does not exist", filepath)
            self.log.info("Starting stream with %s", filepath)
            self.stream_process = subprocess.Popen(["paplay", filepath], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception as error:
            self.log.error("Stream error: %s", error)
            return False

    def stop_a2dp_stream(self):
        """Stop the current A2DP audio stream

        Returns:
            True if the stream was stopped, False otherwise.
        """
        if hasattr(self, 'stream_process') and self.stream_process:
            self.stream_process.terminate()
            self.stream_process = None
            self.log.info("Stream stopped")
            return True
        return False

    def media_control(self, command, address=None):
        """Sends AVRCP (Audio/Video Remote Control Profile) media control commands to a connected Bluetooth device.

        Args:
            command: The AVRCP command to send. Must be one of: "play", "pause", "next", "previous", "rewind".
            address: Bluetooth address of remote device.
        """
        valid = {"play": "Play", "pause": "Pause", "next": "Next", "previous": "Previous", "rewind": "Rewind"}
        if command not in valid:
            self.log.info("Invalid media control command:%s", command)
        media_control_interface = self.get_media_control_interface(address)
        if not media_control_interface:
            self.log.info(" MediaControl1 interface NOT FOUND")
        self.log.info(" MediaControl1 interface FOUND")
        try:
            getattr(media_control_interface, valid[command])()
            self.log.info("AVRCP %s sent successfully to %s", command, address)
        except Exception as error:
            self.log.warning("AVRCP command %s failed with exception : %s", command, error)

    def get_media_control_interface(self, address):
        """Retrieve the `org.bluez.MediaControl1` D-Bus interface for a given Bluetooth device.

        Args:
            address: Bluetooth address of remote device.

        Returns:
            The MediaControl1 D-Bus interface if found, otherwise None.
        """
        try:
            formatted_addr = address.replace(":", "_").upper()
            for path, interfaces in self.object_manager.GetManagedObjects().items():
                if constants.media_control_interface in interfaces:
                    if formatted_addr in path and path.startswith(self.adapter_path):
                        self.log.info("Found MediaControl1 at %s", path)
                        return dbus.Interface(self.bus.get_object(constants.bluez_service, path), constants.media_control_interface)
            self.log.info(" No MediaControl1 interface found for %s under %s", address, self.adapter_path)
        except Exception as error:
            self.log.info(" Exception while getting MediaControl1 interface : %s", error)
        return None

    def get_a2dp_role_for_device(self, device_address):
        """Get the A2DP role (sink or source) for a specific connected Bluetooth device.

        Args:
            device_address: Bluetooth address of remote device.

        Returns:
            str: "sink", "source", or None
        """
        uuid_map = {"source": "110a", "sink": "110b"}
        for path, interfaces in self.object_manager.GetManagedObjects().items():
            if constants.device_interface in interfaces:
                properties = interfaces[constants.device_interface]
                if properties.get("Address") == device_address and properties.get("Connected") and properties.get("Adapter") == self.adapter_path:
                    uuids = properties.get("UUIDs", [])
                    for role, uuid_role in uuid_map.items():
                        if any(uuid_role in uuid.lower() for uuid in uuids):
                            return role
        self.log.warning("Unknown A2DP role %s", device_address)

    def send_file(self, device_address, file_path, session_path=None, profile=None):
        """Send a file via OBEX OPP and wait for real-time transfer status.

        Args:
            device_address: Bluetooth address of remote device.
            file_path: Path to the file to be sent.
            session_path: Existing OBEX session path. If None, a new session is created.
            profile: Bluetooth profile to use for the file transfer.

        Returns:
            Transfer status ("completed", "error", etc.).
        """
        if not os.path.exists(file_path):
            self.log.info("File does not exist: %s", file_path)
            return "error"

        try:
            if not session_path:
                session_path = self.create_obex_session(device_address, profile)

            opp_interface = dbus.Interface(
                self.session_bus.get_object(constants.obex_service, session_path),
                constants.obex_object_push
            )
            transfer_path, _ = opp_interface.SendFile(file_path)
            self.log.info("Started transfer: %s", transfer_path)

            self.transfer_status = {"status": "unknown"}
            self.session_bus.add_signal_receiver(
                self.obex_properties_changed,
                dbus_interface=constants.properties_interface,
                signal_name="PropertiesChanged",
                arg0=constants.obex_object_transfer,
                path=transfer_path,
                path_keyword="path"
            )

            self.transfer_loop = GLib.MainLoop()
            self.transfer_loop.run()

            status = self.transfer_status["status"]
            self.remove_obex_session(session_path)
            return status

        except Exception as error:
            self.log.info("OBEX send failed: %s", error)
            return "error"

    def receive_file(self, save_directory="/tmp", timeout=20, user_confirm_callback=None):
        """Start an OBEX Object Push server and wait for a file to be received.

        Args:
            save_directory: Directory to save received files. Defaults to "/tmp".
            timeout: Time in seconds to wait for a file. Defaults to 20.
            user_confirm_callback: Function to confirm acceptance of received file.

        Returns:
            Full path of accepted received file, or None if no file accepted
        """
        try:
            if not os.path.exists(save_directory):
                os.makedirs(save_directory)
            run(self.log, "killall -9 obexpushd")
            self.log.info("Killed existing obexpushd processes..")
            existing_files = set(os.listdir(save_directory))
            self.opp_process = subprocess.Popen(["obexpushd", "-B", "-o", save_directory, "-n"])
            self.log.info("OPP server started. Waiting for incoming file...")
            start_time = time.time()
            while time.time() - start_time < timeout:
                current_files = set(os.listdir(save_directory))
                new_files = current_files - existing_files
                if new_files:
                    received_file = new_files.pop()
                    full_path = os.path.join(save_directory, received_file)
                    self.log.info("Incoming file: %s", received_file)
                    user_accepted = True
                    if user_confirm_callback:
                        user_accepted = user_confirm_callback(full_path)
                    if user_accepted:
                        self.log.info("User accepted file.")
                        self.stop_opp_receiver()
                        return full_path
                    else:
                        self.log.info("User rejected file.")
                        os.remove(full_path)
                        self.stop_opp_receiver()
        except Exception as error:
            self.stop_opp_receiver()
            self.log.error("Error in receive_file:%s", error)

    def stop_opp_receiver(self):
        """Stop the OBEX Object Push server if it's currently running."""
        if self.opp_process and self.opp_process.poll() is None:
            self.opp_process.terminate()
            self.opp_process.wait()
            self.log.info("OPP server stopped.")
        else:
            self.log.info("No OPP server running or already stopped.")

    def obex_properties_changed(self, interface, changed, invalidated, path):
        """Handle the PropertiesChanged signal for an OBEX file transfer.

        Args:
            interface: The D-Bus interface name where the property change occurred.
            changed: A dictionary containing the properties that changed and their new values.
            invalidated: A list of properties that are no longer valid.
            path: The D-Bus object path for the signal.
        """
        if "Status" in changed:
            status = str(changed["Status"])
            self.log.info("Signal: Transfer status changed to:%s", status)
            self.transfer_status["status"] = status
            if status in ["complete", "error", "cancelled"]:
                if hasattr(self, "transfer_loop") and self.transfer_loop.is_running():
                    self.transfer_loop.quit()
            else:
                self.log.warning("PropertiesChanged received without 'Status': %s", changed)

    def set_discoverable_mode(self, enable):
        """
        Makes the Bluetooth device discoverable.

        Args:
            enable: True to enable, False to disable.
        """
        self.log.info("Setting Bluetooth device to be discoverable...")
        if enable:
            command = f"hciconfig {self.interface} piscan"
            subprocess.run(command, shell=True)
            self.log.info("Bluetooth device is now discoverable.")
        elif not enable:
            self.log.info("Setting Bluetooth device to be non-discoverable...")
            command = f"hciconfig {self.interface} noscan"
            subprocess.run(command, shell=True)
            self.log.info("Bluetooth device is now non-discoverable.")

    def create_obex_session(self, device_address, profile):
        """Creates an OBEX Object Push (OPP) session.

         Args:
            device_address: Bluetooth address of remote device, else return False.
            profile: The bluetooth profile to used for the session.

        Returns:
            session_path: The OBEX session path if successful.
        """
        try:
            self.session_bus = dbus.SessionBus()
            self.obex_manager = dbus.Interface(self.session_bus.get_object(constants.obex_service, constants.obex_path), constants.obex_client)
            session_path = self.obex_manager.CreateSession(device_address, {"Target": dbus.String(profile)})
            self.log.info("Created OBEX OPP session: %s", session_path)
            return session_path
        except Exception as error:
            self.log.error("OBEX session creation failed for device %s: %s", device_address, error)
            return False

    def remove_obex_session(self, session_path):
        """Removes the given OBEX session.

        Args:
            session_path: The OBEX session path to be removed.
        """
        try:
            self.obex_manager.RemoveSession(session_path)
            self.log.info("Removed OBEX session: %s", session_path)
        except Exception as error:
            self.log.warning("Failed to remove session: %s", error)

    def get_media_playback_info(self, address):
        """Retrieve playback status, track info, and position using MediaPlayer1.

        Args:
            address: Bluetooth address of remote device.

        Returns:
             status, track, position (ms), duration (ms), or None if unavailable.
        """
        try:
            formatted_addr = address.replace(":", "_").upper()
            for path, interfaces in self.object_manager.GetManagedObjects().items():
                if constants.media_player_interface in interfaces:
                    if formatted_addr in path and path.startswith(self.adapter_path):
                        media_player = dbus.Interface(self.bus.get_object(constants.bluez_service, path), constants.media_player_interface)
                        props = dbus.Interface(media_player, constants.properties_interface)
                        status = props.Get(constants.media_player_interface, "Status")
                        track = props.Get(constants.media_player_interface, "Track")
                        position = props.Get(constants.media_player_interface, "Position")
                        duration = track.get("Duration", 0)
                        return {
                            "status": str(status),
                            "track": {
                                "title": str(track.get("Title", "")),
                                "artist": str(track.get("Artist", "")),
                                "album": str(track.get("Album", "")),
                            },
                            "position": int(position),
                            "duration": int(duration)
                        }
        except Exception as error:
            self.log.warning("Failed to get media playback info: %s", error)

    def get_media_volume(self, address):
        """Get the current A2DP volume for the given device.

        Args:
            address: Bluetooth address of remote device.

        Returns:
            The volume level as an integer if available, otherwise None.
        """
        try:
            formatted_addr = address.replace(":", "_").upper()
            for path, interfaces in self.object_manager.GetManagedObjects().items():
                if constants.media_transport_interface in interfaces:
                    if formatted_addr in path and path.startswith(self.adapter_path):
                        transport = dbus.Interface(self.bus.get_object(constants.bluez_service, path),
                                                   constants.properties_interface)
                        volume = transport.Get(constants.media_transport_interface, "Volume")
                        return int(volume)
        except Exception as error:
            self.log.warning("Failed to get volume: %s", error)
        return None

    def set_media_volume(self, address, volume):
        """Set A2DP volume (0–127) for the given device.

        Args:
            address: Bluetooth address of remote device.
            volume: Integer volume level to set.

        Returns:
            True if the volume was set successfully, otherwise False.
        """
        try:
            formatted_addr = address.replace(":", "_").upper()
            for path, interfaces in self.object_manager.GetManagedObjects().items():
                if constants.media_transport_interface in interfaces:
                    if formatted_addr in path and path.startswith(self.adapter_path):
                        transport = dbus.Interface(self.bus.get_object(constants.bluez_service, path), constants.properties_interface)
                        transport.Set(constants.media_transport_interface, "Volume", dbus.UInt16(volume))
                        self.log.info("Volume set to %d", volume)
                        return True
        except Exception as error:
            self.log.warning("Failed to set volume: %s", error)
        return False

    def get_connected_profile_uuids(self, device_address):
        """Retrieves the list of UUIDs for the Bluetooth profiles connected to the device
          identified by the given device address.

        Args:
            device_address: Bluetooth address of remote device.

        Returns:
            A list of UUID strings representing the connected profiles.
            Returns an empty list if the UUIDs cannot be retrieved.
        """
        device_path = self.get_device_path(device_address)
        device = dbus.Interface(self.bus.get_object(constants.bluez_service, device_path), constants.device_interface)
        properties = dbus.Interface(self.bus.get_object(constants.bluez_service, device_path),
                                    constants.properties_interface)
        try:
            uuids = properties.Get(constants.device_interface, 'UUIDs')
            return uuids
        except Exception as error:
            self.log.info(f"Failed to get UUIDs for {device_address}: {error}")
            return []

    def connect_profile(self, address, profile_uuid):
        """
        Connect to a specific Bluetooth profile (e.g., A2DP Sink) on the remote device.

        Args:
            address: Bluetooth address of remote device.
            profile_uuid: UUID of the Bluetooth profile to connect.

        Returns:
            True if the profile was connected, False otherwise.
        """
        device_path = self.get_device_path(address)
        try:
            device = dbus.Interface(self.bus.get_object(constants.bluez_service, device_path),
                                    constants.device_interface)
            device.ConnectProfile(profile_uuid)
            self.log.info("Profile %s successfully connected to %s", profile_uuid, address)
            return True
        except Exception as error:
            self.log.error("Failed to connect profile %s: %s", profile_uuid, error)
            return False

    def setup_pairing_signal_listener(self, status_update_handler):
        """Setup D-Bus signal listener for pairing status changes.

        Args:
            status_update_handler: Function to handle pairing status updates.
        """
        self.pairing_status_callback = status_update_handler
        self.bus.add_signal_receiver(
            self.on_pairing_properties_changed,
            dbus_interface="org.freedesktop.DBus.Properties",
            signal_name="PropertiesChanged",
            arg0="org.bluez.Device1",
            path_keyword="path")

    def on_pairing_properties_changed(self, interface, changed, invalidated, path):
        """Listens to changes in "Paired" property in "org.bluez.Device1" interface.

        Args:
            interface: The D-Bus interface name where the property change occurred.
            changed: A dictionary containing the properties that changed and their new values.
            invalidated: A list of properties that are no longer valid.
            path: The D-Bus object path for the signal.
        """
        if interface != "org.bluez.Device1" or "Paired" not in changed:
            return
        paired = changed["Paired"]
        device_address = path.split("dev_")[-1].replace("_", ":")
        if hasattr(self, "pairing_status_callback"):
            self.pairing_status_callback(device_address, paired)

    def get_ofono_modem_path(self, device_address):
        """Gets the ofono modem path.

        Args:
            device_address: Bluetooth address of remote device.
        """
        try:
            manager = dbus.Interface(self.bus.get_object(constants.ofono_bus, "/"), constants.ofono_manager)
            formatted_addr = device_address.replace(":", "_").upper()
            for path, properties in manager.GetModems():
                if formatted_addr in str(path):
                    return path
        except Exception as error:
            self.log.error( "Failed to get oFono modem path: %s", error)

    def answer_call(self, device_address):
        """Answer an incoming call on the device.

        Args:
            device_address: Bluetooth address of remote device.
        """
        path = self.get_ofono_modem_path(device_address)
        if not path:
            self.log.warning("No oFono modem path for %s", device_address)
            return False
        try:
            call_interface = dbus.Interface(self.bus.get_object("org.ofono", self.active_call_path), "org.ofono.VoiceCall")
            call_interface.Answer()
            return True
        except Exception as error:
            self.log.error("Failed to answer call on %s: %s", device_address, error)
            return False

    def hangup_all_calls(self, device_address):
        """Hangs up all the active calls.

        Args:
            device_address: Bluetooth address of remote device.
        """
        path = self.get_ofono_modem_path(device_address)
        if not path:
            self.log.warning("No oFono modem path for %s", device_address)
            return False
        try:
            voice_call_manager = dbus.Interface(self.bus.get_object("org.ofono", path), "org.ofono.VoiceCallManager")
            voice_call_manager.HangupAll()
            return True
        except Exception as error:
            self.log.error("Failed to hangup call on %s: %s", device_address, error)
            return False

    def dial_number(self, device_address, number, hide_callerid="default"):
        """Dial a specific phone number.

        Args:
            device_address: Bluetooth address of remote device.
            number: Number typed by user.
            hide_callerid: whether to hide caller id or not.
        """
        path = self.get_ofono_modem_path(device_address)
        if not path:
            self.log.warning("No oFono modem path for %s", device_address)
            return False
        try:
            voice_call_manager = dbus.Interface(self.bus.get_object("org.ofono", path),"org.ofono.VoiceCallManager")
            call_path = voice_call_manager.Dial(number, hide_callerid)
            self.log.info("Dialed number %s on %s, call path: %s", number, device_address, call_path)
            return call_path
        except Exception as error:
            self.log.error("Failed to dial on %s: %s", device_address, error)
            return False

    def dial_last(self, device_address):
        """Initiates a new outgoing call to the last dialled number.

        Args:
            device_address: Bluetooth address of remote device.
        """
        path = self.get_ofono_modem_path(device_address)
        if not path:
            self.log.warning("No oFono modem path for %s", device_address)
            return False
        try:
            voice_call_manager = dbus.Interface(self.bus.get_object("org.ofono", path),"org.ofono.VoiceCallManager")
            call_path = voice_call_manager.DialLast()
            self.log.info("Dialed number %s on %s, call path: %s", device_address, call_path)
            return call_path
        except Exception as error:
            self.log.error("Failed to dial on %s: %s", device_address, error)
            return False

    def set_call_volume(self, device_address, volume):
        """Set the call volume (0-100).

        Args:
            device_address: Bluetooth address of remote device.
            volume: Volume level input to be set for the call.
        """
        path = self.get_ofono_modem_path(device_address)
        if not path:
            self.log.warning(f"No ofono path for {device_address}")
            return False
        try:
            call_volume = dbus.Interface(self.bus.get_object("org.ofono", path), "org.ofono.CallVolume")
            call_volume.SetVolume(volume)
            return True
        except Exception as error:
            self.log.error(f"Failed to set volume on {device_address}: {error}")
            return False

    def hangup_active_call(self):
        """Hang up the current active call."""
        if not self.active_call_path:
            self.log.warning("No active call to hang up.")
            return
        try:
            call_interface = dbus.Interface(self.bus.get_object("org.ofono", self.active_call_path), "org.ofono.VoiceCall")
            call_interface.Hangup()
            self.log.info(f"Hung up call: {self.active_call_path}")
        except Exception as error:
            self.log.error(f"Failed to hang up: {error}")

    def on_call_added(self, call_path, properties):
        """Triggered when a new call starts or incoming call detected."""
        self.active_call_path = call_path
        number = properties.get("LineIdentification", "Unknown")
        state = properties.get("State", "unknown")
        self.log.info(f"New call: {call_path}, Number={number}, State={state}")

    def on_call_removed(self, call_path):
        """Triggered when a call ends."""
        if self.active_call_path == call_path:
            self.log.info(f"Call ended: {call_path}")
            self.active_call_path = None

    def setup_hfp_manager(self, device_address):
        """Initialize oFono VoiceCallManager and connect to call signals.

        Args:
            device_address: Bluetooth address of remote device.
        """
        path = self.get_ofono_modem_path(device_address)
        if not path:
            self.log.warning(f"No ofono path for {device_address}")
            return
        try:
            self.voice_call_manager = dbus.Interface(self.bus.get_object("org.ofono", path),
                                                     "org.ofono.VoiceCallManager")
            self.voice_call_manager.connect_to_signal("CallAdded", self.on_call_added)
            self.voice_call_manager.connect_to_signal("CallRemoved", self.on_call_removed)

            self.log.info(f"VoiceCallManager initialized for {device_address}")
        except Exception as error:
            self.log.error(f"Failed to setup VoiceCallManager for {device_address}: {error}")