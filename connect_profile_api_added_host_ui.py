import os
import re

from PyQt6.QtCore import QCoreApplication, QParallelAnimationGroup, QEasingCurve, QPropertyAnimation
from PyQt6.QtCore import Qt
from PyQt6.QtCore import QFileSystemWatcher
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QCheckBox, QInputDialog, QToolButton, QGraphicsDropShadowEffect
from PyQt6.QtWidgets import QComboBox
from PyQt6.QtWidgets import QDialog
from PyQt6.QtWidgets import QDialogButtonBox
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtWidgets import QGridLayout
from PyQt6.QtWidgets import QGroupBox
from PyQt6.QtWidgets import QHeaderView
from PyQt6.QtWidgets import QHBoxLayout
from PyQt6.QtWidgets import QLabel
from PyQt6.QtWidgets import QLayout
from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtWidgets import QListWidget
from PyQt6.QtWidgets import QListWidgetItem
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtWidgets import QRadioButton
from PyQt6.QtWidgets import QSizePolicy
from PyQt6.QtWidgets import QSlider
from PyQt6.QtWidgets import QTabWidget
from PyQt6.QtWidgets import QTableWidget
from PyQt6.QtWidgets import QTableWidgetItem
from PyQt6.QtWidgets import QTabWidget
from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtWidgets import QVBoxLayout
from PyQt6.QtWidgets import QWidget

import style_sheet as styles
from libraries.bluetooth import constants
from libraries.bluetooth.bluez_test import BluetoothDeviceManager
from Utils.utils import get_controller_interface_details
from Utils.utils import validate_bluetooth_address


class TestApplication(QWidget):
    """Main GUI class for the Bluetooth Test Host."""

    def __init__(self, interface=None, back_callback=None, log=None, bluetoothd_log_file_path=None, pulseaudio_log_file_path=None, obexd_log_file_path=None, ofonod_log_file_path=None, hcidump_log_name=None):
        """Initialize the Test Host widget.

        Args:
            interface: Bluetooth adapter interface (e.g., hci0).
            back_callback: Optional callback to trigger on back action.
            log: Logger instance used for logging.
             bluetoothd_log_file_path: Path to bluetoothd log.
            pulseaudio_log_file_path: Path to PulseAudio log.
            obexd_log_file_path: Path to obexd log.
            ofonod_log_file_path: Path to ofonod log.
            hcidump_log_name: Name of hcidump log file.
        """
        super().__init__()
        self.interface = interface
        self.log_path = log.log_path
        self.log = log
        self.bluetoothd_log_file_path = bluetoothd_log_file_path
        self.pulseaudio_log_file_path = pulseaudio_log_file_path
        self.obexd_log_file_path = obexd_log_file_path
        self.ofonod_log_file_path = ofonod_log_file_path
        self.hcidump_log_name = hcidump_log_name
        self.back_callback = back_callback
        self.bluetooth_device_manager = BluetoothDeviceManager(log=self.log, interface=self.interface)
        self.paired_devices = {}
        self.main_grid_layout = None
        self.gap_button = None
        self.device_tab_widget = None
        self.device_profiles = {}
        self.grid = None
        self.playback_timer = None
        self.profile_methods_layout = None
        self.profile_methods_widget = None
        self.profiles_list_widget = None
        self.profile_description_text_browser = None
        self.refresh_button = None
        self.hfp_sections = []
        self.current_expanded_section = None

        self.selected_profiles = {}
        self.device_tabs_map = {}
        self.device_states = {}
        self.setup_pairing_status_listener()
        self.initialize_host_ui()

    def load_paired_devices(self):
        """Loads and displays all paired Bluetooth devices into the profiles list widget."""
        list_index = self.profiles_list_widget.count() - 1
        self.paired_devices = self.bluetooth_device_manager.get_paired_devices()
        unique_devices = set(self.paired_devices.keys())
        for device_address in unique_devices:
            device_item = QListWidgetItem(device_address)
            device_item.setFont(QFont("Courier New", 10))
            device_item.setForeground(Qt.GlobalColor.black)
            list_index += 1
            self.profiles_list_widget.insertItem(list_index, device_item)

    def add_controller_details_row(self, row, label, value):
        """Adds a new row to the controller details grid layout.

        Args:
            row: The row index in the grid layout where this entry should be placed.
            label: The text label to describe the data.
            value: The corresponding value to display alongside the label.
        """
        label_widget = QLabel(label)
        label_widget.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        label_widget.setObjectName("label_widget")
        label_widget.setStyleSheet(styles.color_style_sheet)
        value_widget = QLabel(value)
        value_widget.setObjectName("value_widget")
        value_widget.setFont(QFont("Arial", 10))
        value_widget.setStyleSheet(styles.color_style_sheet)
        self.grid.addWidget(label_widget, row, 0)
        self.grid.addWidget(value_widget, row, 1)

    def set_discoverable_mode(self, enable):
        """Enable or disable discoverable mode on the Bluetooth adapter.

        Args:
            enable: True to enable, False to disable.
        """
        if enable:
            self.set_discoverable_on_button.setEnabled(False)
            self.set_discoverable_off_button.setEnabled(True)
            self.bluetooth_device_manager.set_discoverable_mode(True)
            timeout = int(self.discoverable_timeout_input.text())
            if timeout > 0:
                self.discoverable_timeout_timer = QTimer()
                self.discoverable_timeout_timer.timeout.connect(lambda: self.set_discoverable_mode(False))
                self.discoverable_timeout_timer.setSingleShot(True)
                self.discoverable_timeout_timer.start(timeout * 1000)
            self.log.info("Discoverable mode is set to ON")
        else:
            self.set_discoverable_on_button.setEnabled(True)
            self.set_discoverable_off_button.setEnabled(False)
            self.bluetooth_device_manager.set_discoverable_mode(False)
            if hasattr(self, 'discoverable_timeout_timer'):
                self.discoverable_timeout_timer.stop()
            self.log.info("Discoverable mode is set to OFF")

    def start_device_discovery(self):
        """Start device discovery."""
        self.inquiry_timeout = int(self.inquiry_timeout_input.text()) * 1000
        if self.inquiry_timeout == 0:
            self.set_discovery_on_button.setEnabled(False)
            self.set_discovery_off_button.setEnabled(True)
            self.bluetooth_device_manager.start_discovery()
        else:
            self.timer = QTimer()
            self.timer.timeout.connect(self.handle_discovery_timeout)
            self.timer.timeout.connect(lambda: self.set_discovery_off_button.setEnabled(False))
            self.timer.start(self.inquiry_timeout)
            self.set_discovery_on_button.setEnabled(False)
            self.set_discovery_off_button.setEnabled(True)
            self.bluetooth_device_manager.start_discovery()
        self.log.info("Device discovery has started")

    def handle_discovery_timeout(self):
        """Handles the Bluetooth discovery timeout event"""
        self.timer.stop()
        self.bluetooth_device_manager.stop_discovery()
        self.log.info("Discovery stopped due to timeout.")
        self.display_discovered_devices()

    def stop_device_discovery(self):
        """Stops device Discovery"""
        self.set_discovery_off_button.setEnabled(False)
        self.timer = QTimer()
        if self.inquiry_timeout == 0:
            self.bluetooth_device_manager.stop_discovery()
            self.display_discovered_devices()
        else:
            self.timer.stop()
            self.bluetooth_device_manager.stop_discovery()
            self.display_discovered_devices()
            self.set_discovery_off_button.setEnabled(False)
        self.log.info("Device discovery has stopped")

    def display_discovered_devices(self):
        """Display discovered devices in a table with options to pair or connect."""
        self.timer.stop()
        bold_font = QFont()
        bold_font.setBold(True)
        small_font = QFont()
        small_font.setBold(True)
        small_font.setPointSize(8)
        discovered_devices = self.bluetooth_device_manager.get_discovered_devices()
        self.clear_device_discovery_results()
        self.table_widget = QTableWidget(0, 3)
        self.table_widget.setHorizontalHeaderLabels(["DEVICE NAME", "BD_ADDR", "PROCEDURES"])
        self.table_widget.setFont(bold_font)
        header = self.table_widget.horizontalHeader()
        header.setStyleSheet(styles.horizontal_header_style_sheet)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        vertical_header = self.table_widget.verticalHeader()
        vertical_header.setStyleSheet(styles.vertical_header_style_sheet)
        row = 0
        for device in discovered_devices:
            device_address = device["address"]
            device_name = device["alias"]
            device_path = device["path"]
            self.table_widget.insertRow(row)
            self.table_widget.setItem(row, 0, QTableWidgetItem(device_name))
            self.table_widget.setItem(row, 1, QTableWidgetItem(device_address))
            button_widget = QWidget()
            button_layout = QHBoxLayout()
            button_layout.setContentsMargins(0, 0, 0, 0)
            button_layout.setSpacing(5)
            pair_button = QPushButton("PAIR")
            pair_button.setObjectName("PairButton")
            pair_button.setFont(small_font)
            pair_button.setStyleSheet(styles.color_style_sheet)
            pair_button.clicked.connect(lambda _, addr = device_address: self.perform_device_action('pair', addr, load_profiles=False))
            button_layout.addWidget(pair_button)
            connect_button = QPushButton("CONNECT")
            connect_button.setObjectName("ConnectButton")
            connect_button.setFont(small_font)
            connect_button.setStyleSheet(styles.color_style_sheet)
            connect_button.clicked.connect(lambda _, addr = device_address: self.perform_device_action('connect', addr, load_profiles=True))
            button_layout.addWidget(connect_button)
            button_widget.setLayout(button_layout)
            self.table_widget.setCellWidget(row, 2, button_widget)
            row += 1
        self.profile_methods_layout.insertWidget(self.profile_methods_layout.count() - 1, self.table_widget)
        self.table_widget.show()
        self.set_discovery_off_button.setEnabled(False)

    def clear_device_discovery_results(self):
        """Removes the discovery table if it exists to avoid stacking."""
        if hasattr(self, 'table_widget') and self.table_widget:
            self.profile_methods_layout.removeWidget(self.table_widget)
            self.table_widget.deleteLater()
            self.table_widget = None

    def refresh_discovery_ui(self):
        """Refresh and clear the device discovery table."""
        self.log.info("Refresh Button is pressed")
        if hasattr(self, 'table_widget') and self.table_widget:
            self.profile_methods_layout.removeWidget(self.table_widget)
            self.table_widget.deleteLater()
            self.table_widget = None
            self.inquiry_timeout_input.setText("0")
            self.refresh_button.setEnabled(False)
            self.set_discovery_on_button.setEnabled(True)
            self.set_discovery_off_button.setEnabled(False)
            self.refresh_button.setEnabled(True)

    def reset_discoverable_timeout(self):
        """Reset discoverable timeout input to default (0)."""
        self.log.info("Discoverable refresh button is pressed")
        self.discoverable_timeout_input.setText("0")

    def add_paired_device_to_list(self, device_address):
        """Adds a device address to the paired devices list if not already present.

        Args:
            device_address: Bluetooth address of remote device.
        """
        for i in range(self.profiles_list_widget.count()):
            if self.profiles_list_widget.item(i).text().strip() == device_address:
                return
        device_item = QListWidgetItem(device_address)
        device_item.setFont(QFont("Courier New", 10))
        device_item.setForeground(Qt.GlobalColor.black)
        self.profiles_list_widget.addItem(device_item)

    def clear_layout(self, layout):
        """Delete all widgets and sub-layouts from a layout.

        Args:
            layout: The layout to be cleared.
        """
        if not isinstance(layout, QLayout):
            return
        while layout.count():
            item = layout.takeAt(0)
            if child_layout := item.layout():
                self.clear_layout(child_layout)
            elif widget := item.widget():
                widget.setParent(None)
                widget.deleteLater()

    def handle_profile_selection(self, profile_name=None):
        """Handles profile selection from either the list or a button.

        Args:
            profile_name: The name of the profile to select.
        """
        if profile_name is None:
            selected_item = self.profiles_list_widget.currentItem()
            if not selected_item:
                return
            selected_item_text = selected_item.text().strip()
        else:
            selected_item_text = profile_name.strip()
        self.clear_device_discovery_results()
        self.clear_profile_ui()
        if hasattr(self, 'device_tab_widget') and self.device_tab_widget:
            self.device_tab_widget.currentChanged.disconnect(self.handle_profile_tab_change)
            self.profile_methods_layout.removeWidget(self.device_tab_widget)
            self.device_tab_widget.hide()
            self.device_tab_widget.setParent(None)
            self.device_tab_widget.deleteLater()
            self.device_tab_widget = None
        if validate_bluetooth_address(selected_item_text):
            self.load_device_profile_tabs(selected_item_text, self.device_profiles.get(selected_item_text, []))
        elif selected_item_text == "GAP":
            self.create_gap_profile_ui()

    def create_gap_profile_ui(self):
        """Build and display the widgets for the GAP profile."""
        bold_font = QFont()
        bold_font.setBold(True)
        label = QLabel("SetDiscoverable: ")
        label.setObjectName("SetDiscoverable")
        label.setFont(bold_font)
        label.setStyleSheet(styles.color_style_sheet)
        self.profile_methods_layout.addWidget(label)
        timeout_layout = QHBoxLayout()
        timeout_label = QLabel("SetDiscoverable Timeout: ")
        timeout_label.setObjectName("SetDiscoverableTimeout")
        timeout_label.setFont(bold_font)
        timeout_label.setStyleSheet(styles.color_style_sheet)
        self.discoverable_timeout_input = QLineEdit("0")
        timeout_layout.addWidget(timeout_label)
        timeout_layout.addWidget(self.discoverable_timeout_input)
        self.profile_methods_layout.addLayout(timeout_layout)
        buttons_layout = QHBoxLayout()
        self.set_discoverable_on_button = QPushButton("ON")
        self.set_discoverable_on_button.setObjectName("SetDiscoverableOnButton")
        self.set_discoverable_on_button.setStyleSheet(styles.color_style_sheet)
        self.set_discoverable_off_button = QPushButton("OFF")
        self.set_discoverable_off_button.setObjectName("SetDiscoverableOffButton")
        self.set_discoverable_off_button.setStyleSheet(styles.color_style_sheet)
        self.set_discoverable_off_button.setEnabled(False)
        self.set_discoverable_on_button.clicked.connect(lambda: self.set_discoverable_mode(True))
        self.set_discoverable_off_button.clicked.connect(lambda: self.set_discoverable_mode(False))
        buttons_layout.addWidget(self.set_discoverable_on_button)
        buttons_layout.addWidget(self.set_discoverable_off_button)
        self.profile_methods_layout.addLayout(buttons_layout)
        self.refresh_button = QPushButton("REFRESH")
        self.refresh_button.setObjectName("RefreshButton")
        self.refresh_button.setStyleSheet(styles.color_style_sheet)
        self.refresh_button.clicked.connect(self.reset_discoverable_timeout)
        self.profile_methods_layout.addWidget(self.refresh_button)
        inquiry_label = QLabel("Inquiry:")
        inquiry_label.setObjectName("Inquiry")
        inquiry_label.setFont(bold_font)
        inquiry_label.setStyleSheet(styles.color_style_sheet)
        self.profile_methods_layout.addWidget(inquiry_label)
        inquiry_timeout_layout = QHBoxLayout()
        inquiry_timeout_label = QLabel("Inquiry Timeout:")
        inquiry_timeout_label.setObjectName("InquiryTimeoutLabel")
        inquiry_timeout_label.setFont(bold_font)
        inquiry_timeout_label.setStyleSheet(styles.color_style_sheet)
        self.inquiry_timeout_input = QLineEdit("0")
        inquiry_timeout_layout.addWidget(inquiry_timeout_label)
        inquiry_timeout_layout.addWidget(self.inquiry_timeout_input)
        self.profile_methods_layout.addLayout(inquiry_timeout_layout)
        discovery_buttons_layout = QHBoxLayout()
        self.set_discovery_on_button = QPushButton("START")
        self.set_discovery_on_button.setObjectName("SetDiscoveryOnButton")
        self.set_discovery_on_button.setStyleSheet(styles.color_style_sheet)
        self.set_discovery_on_button.clicked.connect(self.start_device_discovery)
        self.set_discovery_off_button = QPushButton("STOP")
        self.set_discovery_off_button.setObjectName("SetDiscoveryOffButton")
        self.set_discovery_off_button.setStyleSheet(styles.color_style_sheet)
        self.set_discovery_off_button.clicked.connect(self.stop_device_discovery)
        self.set_discovery_off_button.setEnabled(False)
        discovery_buttons_layout.addWidget(self.set_discovery_on_button)
        discovery_buttons_layout.addWidget(self.set_discovery_off_button)
        self.profile_methods_layout.addLayout(discovery_buttons_layout)
        capability_label = QLabel("Select Capability: ")
        capability_label.setFont(bold_font)
        self.capability_combobox = QComboBox()
        self.capability_combobox.setFont(QFont("Arial", 10))
        self.capability_combobox.addItems(
            ["DisplayOnly", "DisplayYesNo", "KeyboardOnly", "NoInputNoOutput", "KeyboardDisplay"])
        self.capability_combobox.setCurrentText("NoInputNoOutput")
        register_agent_button = QPushButton("Register Agent")
        register_agent_button.setObjectName("RegisterAgent")
        register_agent_button.setFont(bold_font)
        register_agent_button.setStyleSheet(styles.color_style_sheet)
        register_agent_button.clicked.connect(self.register_bluetooth_agent)
        self.profile_methods_layout.addWidget(capability_label)
        self.profile_methods_layout.addWidget(self.capability_combobox)
        self.profile_methods_layout.addWidget(register_agent_button)
        discovery_refresh_button = QPushButton("REFRESH")
        discovery_refresh_button.setObjectName("RefreshButton")
        discovery_refresh_button.setStyleSheet(styles.color_style_sheet)
        discovery_refresh_button.clicked.connect(self.refresh_discovery_ui)
        self.profile_methods_layout.addWidget(discovery_refresh_button)
        self.profile_methods_layout.addStretch(1)

    def create_a2dp_profile_ui(self, device_address):
        """Build and display the widgets for the A2DP profile.

        Args:
             device_address: The Bluetooth address of the device.
        """
        bold_font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        a2dp_label = QLabel("<b>A2DP Functionality</b>")
        a2dp_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        a2dp_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(a2dp_label)
        self.device_address_source = device_address
        self.device_address_sink = device_address
        role = self.bluetooth_device_manager.get_a2dp_role_for_device(device_address)
        self.log.debug("A2DP role for %s:%s", device_address, role)
        if role in ["source"]:
            self.create_a2dp_sink_ui(layout, bold_font)
        if role in ["sink"]:
            self.create_a2dp_source_ui(layout, bold_font)
        layout.addStretch(1)
        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def create_a2dp_sink_ui(self, layout, bold_font):
        """create and add the A2DP Sink UI elements to the give layout.

        Args:
             layout: Parent layout to add the UI.
             bold_font: Font for bold labels and buttons.
        """
        media_control_group = QGroupBox("Media Control (A2DP Sink)")
        media_control_group.setStyleSheet(styles.bluetooth_profiles_groupbox_style)
        media_control_layout = QVBoxLayout()
        media_control_layout.setSpacing(12)
        media_info_grid = QGridLayout()
        media_info_grid.setContentsMargins(0, 0, 0, 0)
        media_info_grid.setSpacing(5)
        title_label = QLabel("Title:")
        artist_label = QLabel("Artist:")
        album_label = QLabel("Album:")
        for label in [title_label, artist_label, album_label]:
            label.setFont(bold_font)
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.song_title_label = QLabel("Unknown")
        self.song_artist_label = QLabel("-")
        self.song_album_label = QLabel("-")
        for label in [self.song_title_label, self.song_artist_label, self.song_album_label]:
            label.setWordWrap(True)
            label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        media_info_grid.addWidget(title_label, 0, 0)
        media_info_grid.addWidget(self.song_title_label, 0, 1)
        media_info_grid.addWidget(artist_label, 1, 0)
        media_info_grid.addWidget(self.song_artist_label, 1, 1)
        media_info_grid.addWidget(album_label, 2, 0)
        media_info_grid.addWidget(self.song_album_label, 2, 1)
        media_info_grid.setColumnStretch(1, 1)
        media_control_layout.addLayout(media_info_grid)
        control_buttons = QHBoxLayout()
        self.play_button = QPushButton("Play")
        self.pause_button = QPushButton("Pause")
        self.next_button = QPushButton("Next")
        self.previous_button = QPushButton("Previous")
        self.rewind_button = QPushButton("Rewind")
        for button, action in [
            (self.play_button, "play"),
            (self.pause_button, "pause"),
            (self.next_button, "next"),
            (self.previous_button, "previous"),
            (self.rewind_button, "rewind")
        ]:
            button.setStyleSheet(styles.bluetooth_profiles_button_style)
            button.setFont(bold_font)
            button.clicked.connect(lambda _, a=action: self.send_media_control_command(a))
            control_buttons.addWidget(button)
        media_control_layout.addLayout(control_buttons)
        self.track_status_label = QLabel("Status: -")
        self.track_status_label.setFont(bold_font)
        self.track_status_label.setFont(QFont("Segoe UI", 9))
        self.track_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        media_control_layout.addWidget(self.track_status_label)
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.setRange(0, 100)
        self.progress_slider.setEnabled(False)
        self.progress_slider.setStyleSheet(styles.progress_slider_style_sheet)
        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(4)
        progress_layout.addWidget(self.progress_slider)
        time_layout = QHBoxLayout()
        time_layout.setContentsMargins(2, 0, 2, 0)
        self.elapsed_time_label = QLabel("00:00")
        self.elapsed_time_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.remaining_time_label = QLabel("00:00")
        self.remaining_time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        time_layout.addWidget(self.elapsed_time_label)
        time_layout.addStretch()
        time_layout.addWidget(self.remaining_time_label)
        progress_layout.addLayout(time_layout)
        media_control_layout.addLayout(progress_layout)
        volume_layout = QHBoxLayout()
        volume_label = QLabel("Volume:")
        volume_label.setFont(bold_font)
        volume_layout.addWidget(volume_label)
        self.sink_volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.sink_volume_slider.setRange(0, 127)
        self.sink_volume_slider.setFixedWidth(150)
        self.sink_volume_slider.setStyleSheet(styles.volume_slider_style_sheet)
        self.sink_volume_slider.setEnabled(True)
        self.sink_volume_slider.valueChanged.connect(self.set_device_volume)
        self.volume_value_label = QLabel("100%")
        self.sink_volume_slider.valueChanged.connect(
            lambda v: self.volume_value_label.setText(f"{int(v / 127 * 100)}%"))
        volume_layout.addWidget(self.sink_volume_slider)
        volume_layout.addWidget(self.volume_value_label)
        media_control_layout.addLayout(volume_layout)
        media_control_group.setLayout(media_control_layout)
        layout.addWidget(media_control_group)
        self.volume_control()
        self.start_media_playback_timer()

    def create_a2dp_source_ui(self, layout, bold_font):
        """create and add the A2DP Source UI elements to the give layout.

        Args:
            layout: Parent layout to add the UI.
            bold_font: Font for bold labels and buttons.
        """
        streaming_group = QGroupBox("Streaming Audio (A2DP Source)")
        streaming_group.setStyleSheet(styles.bluetooth_profiles_groupbox_style)
        streaming_layout = QVBoxLayout()
        streaming_layout.setSpacing(10)
        streaming_layout.setContentsMargins(10, 10, 10, 10)
        self.source_status_label = QLabel("Status: Not Streaming")
        self.source_status_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        streaming_layout.addWidget(self.source_status_label)
        audio_playlist_layout = QVBoxLayout()
        playlist_label = QLabel("Audio Playlist:")
        playlist_label.setFont(bold_font)
        audio_playlist_layout.addWidget(playlist_label)
        self.audio_playlist = QListWidget()
        self.audio_playlist.setFixedHeight(100)
        self.audio_playlist.setFixedHeight(100)
        audio_playlist_layout.addWidget(self.audio_playlist)
        playlist_buttons = QHBoxLayout()
        self.add_files_button = QPushButton("Add Files")
        self.add_files_button.setStyleSheet(styles.bluetooth_profiles_button_style)
        self.add_files_button.clicked.connect(self.select_audio_file)
        self.remove_selected_button = QPushButton("Remove Selected")
        self.remove_selected_button.setStyleSheet(styles.bluetooth_profiles_button_style)
        self.remove_selected_button.clicked.connect(self.remove_selected_file)
        self.clear_playlist_button = QPushButton("Clear")
        self.clear_playlist_button.setStyleSheet(styles.bluetooth_profiles_button_style)
        self.clear_playlist_button.clicked.connect(self.clear_playlist)
        playlist_buttons.addWidget(self.add_files_button)
        playlist_buttons.addWidget(self.remove_selected_button)
        playlist_buttons.addWidget(self.clear_playlist_button)
        audio_playlist_layout.addLayout(playlist_buttons)
        streaming_layout.addLayout(audio_playlist_layout)
        volume_layout = QHBoxLayout()
        volume_label = QLabel("Volume:")
        volume_label.setFont(bold_font)
        volume_layout.addWidget(volume_label)
        self.source_volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.source_volume_slider.setRange(0, 100)
        self.source_volume_slider.setValue(100)
        self.source_volume_slider.setFixedWidth(150)
        self.source_volume_slider.setStyleSheet(styles.volume_slider_style_sheet)
        self.source_volume_slider.valueChanged.connect(self.set_source_volume)
        self.source_volume_label = QLabel("100%")
        self.source_volume_slider.valueChanged.connect(lambda v: self.source_volume_label.setText(f"{v}%"))
        volume_layout.addWidget(self.source_volume_slider)
        volume_layout.addWidget(self.source_volume_label)
        streaming_layout.addLayout(volume_layout)
        streaming_buttons_layout = QHBoxLayout()
        self.start_streaming_button = QPushButton("Start Streaming")
        self.start_streaming_button.setStyleSheet(styles.bluetooth_profiles_button_style)
        self.start_streaming_button.clicked.connect(self.start_a2dp_streaming)
        self.stop_streaming_button = QPushButton("Stop Streaming")
        self.stop_streaming_button.setStyleSheet(styles.bluetooth_profiles_button_style)
        self.stop_streaming_button.clicked.connect(self.stop_a2dp_streaming)
        self.stop_streaming_button.setEnabled(False)
        streaming_buttons_layout.addWidget(self.start_streaming_button)
        streaming_buttons_layout.addWidget(self.stop_streaming_button)
        streaming_layout.addLayout(streaming_buttons_layout)
        streaming_group.setLayout(streaming_layout)
        layout.addWidget(streaming_group)

    def create_opp_profile_ui(self, device_address):
        """Builds and returns the OPP (Object Push Profile) panel for Bluetooth file transfer.

        Args:
            device_address: The Bluetooth address of the device.
        """
        bold_font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        opp_label = QLabel("<b>OPP Functionality</b>")
        opp_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        opp_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(opp_label)
        session_path = self.device_states.get(device_address, {}).get("session_path")
        if not session_path:
            warning_label = QLabel("Device is not connected. Connect to enable OPP profile.")
            warning_label.setObjectName("WarningLabel")
            warning_label.setFont(bold_font)
            warning_label.setStyleSheet(styles.color_style_sheet)
            layout.addWidget(warning_label)
            layout.addStretch(1)
            widget = QWidget()
            widget.setLayout(layout)
            widget.setStyleSheet(styles.device_tab_widget_style_sheet)
            return widget
        opp_group = QGroupBox("File Transfer")
        opp_group.setStyleSheet(styles.bluetooth_profiles_groupbox_style)
        opp_layout = QVBoxLayout()
        opp_layout.setSpacing(10)
        opp_layout.setContentsMargins(10, 10, 10, 10)
        file_selection_layout = QHBoxLayout()
        file_label = QLabel("Select File:")
        file_label.setFont(bold_font)
        file_selection_layout.addWidget(file_label)
        self.opp_location_input = QLineEdit()
        self.opp_location_input.setReadOnly(True)
        self.opp_location_input.setFixedHeight(28)
        file_selection_layout.addWidget(self.opp_location_input)
        self.browse_opp_button = QPushButton("Browse")
        self.browse_opp_button.setFont(bold_font)
        self.browse_opp_button.setStyleSheet(styles.bluetooth_profiles_button_style)
        self.browse_opp_button.clicked.connect(self.select_opp_file)
        file_selection_layout.addWidget(self.browse_opp_button)
        opp_layout.addLayout(file_selection_layout)
        button_layout = QHBoxLayout()
        self.send_file_button = QPushButton("Send File")
        self.send_file_button.setFont(bold_font)
        self.send_file_button.setStyleSheet(styles.bluetooth_profiles_button_style)
        self.send_file_button.clicked.connect(self.send_file)
        button_layout.addWidget(self.send_file_button)
        self.receive_file_button = QPushButton("Receive File")
        self.receive_file_button.setFont(bold_font)
        self.receive_file_button.setStyleSheet(styles.bluetooth_profiles_button_style)
        self.receive_file_button.clicked.connect(self.receive_file)
        button_layout.addWidget(self.receive_file_button)
        opp_layout.addLayout(button_layout)
        opp_group.setLayout(opp_layout)
        layout.addWidget(opp_group)
        layout.addStretch(1)
        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def send_media_control_command(self, command):
        """Sends a media control command to the connected Bluetooth device.

        Args:
            command: The media control command to send (e.g., "play", "pause", "next", "previous").
        """
        self.bluetooth_device_manager.media_control(command, address=self.device_address_sink)
        self.log.info("Media command %s sent to device %s.", command, self.device_address_sink)

    def start_a2dp_streaming(self):
        """Start A2DP streaming to a selected Bluetooth sink device."""
        selected_items = self.audio_playlist.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No File Selected", "Please select an audio file from the playlist.")
            return
        audio_path = selected_items[0].text().strip()
        if not os.path.exists(audio_path):
            QMessageBox.warning(self, "Invalid Audio File", "Selected file does not exist.")
            return
        if not self.device_address_source:
            QMessageBox.warning(self, "No Device", "Please select a Bluetooth sink device to stream.")
            return
        self.log.info("A2DP streaming started with file: %s", audio_path)
        self.start_streaming_button.setEnabled(False)
        self.stop_streaming_button.setEnabled(True)
        self.source_status_label.setText("Status: Streaming")
        status = self.bluetooth_device_manager.start_a2dp_stream(self.device_address_source, audio_path)
        if not status:
            QMessageBox.critical(self, "Streaming Failed", "Failed to start streaming.")
            self.start_streaming_button.setEnabled(True)
            self.stop_streaming_button.setEnabled(False)
            self.source_status_label.setText("Status: Failed")

    def stop_a2dp_streaming(self):
        """Stop active A2DP streaming session."""
        self.log.info("A2DP streaming stopped")
        self.start_streaming_button.setEnabled(True)
        self.stop_streaming_button.setEnabled(False)
        self.source_status_label.setText("Status: Stopped")
        self.bluetooth_device_manager.stop_a2dp_stream()
        if hasattr(self, 'streaming_timer'):
            self.streaming_timer.stop()

    def select_audio_file(self):
        """Browse and add multiple audio files to playlist."""
        files, _ = QFileDialog.getOpenFileNames(caption="Select Audio File", filter="WAV files (*.wav)")
        invalid_files = []
        for file_path in files:
            if os.path.exists(file_path):
                self.audio_playlist.addItem(file_path)
            else:
                invalid_files.append(file_path)
        if invalid_files:
            warning_msg = "The following files were not found and were not added:\n" + "\n".join(invalid_files)
            QMessageBox.warning(self, "File Not Found", warning_msg)

    def select_opp_file(self):
        """Open a file dialog to select a file to send via OPP."""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(None, "Select File to Send via OPP", "", "All Files (*)")
        if file_path:
            if not os.path.exists(file_path):
                QMessageBox.critical(None, "Invalid File", "The selected file does not exist.")
                self.log.error("Selected OPP file does not exist: %s", file_path)
                return
            self.opp_location_input.setText(file_path)
            self.log.info("File selected to send via OPP")

    def send_file(self):
        """Send a selected file to a remote device using OPP."""
        file_path = self.opp_location_input.text()
        session_path = self.device_states.get(self.device_address, {}).get("session_path")
        if not file_path or not self.device_address:
            QMessageBox.warning(None, "OPP", "Please select a device and a file.")
            return
        self.send_file_button.setEnabled(False)
        self.send_file_button.setText("Sending...")
        try:
            status = self.bluetooth_device_manager.send_file(self.device_address, file_path, session_path)
        except Exception as error:
            status = "error"
            self.log.info("UI error:%s", error)
        self.send_file_button.setEnabled(True)
        self.send_file_button.setText("Send File")
        if status == "complete":
            QMessageBox.information(None, "OPP", "File sent successfully!")
        elif status == "queued":
            QMessageBox.information(None, "OPP", "File transfer is queued. Please wait...")
        elif status == "unknown":
            QMessageBox.warning(None, "OPP", "File transfer status is unknown.")
        else:
            QMessageBox.warning(None, "OPP", "File transfer failed or was rejected.")

    def receive_file(self):
        """Start OPP receiver and handle file transfer."""
        try:
            received_file_path = self.bluetooth_device_manager.receive_file(
                user_confirm_callback=self.prompt_file_transfer_confirmation)
            if received_file_path:
                QMessageBox.information(None, "File Received", f"File received successfully:\n{received_file_path}")
            else:
                QMessageBox.warning(None, "File Transfer", "No file received or user declined the transfer.")
        except Exception as error:
            QMessageBox.critical(None, "Error", f"An error occurred during file reception:\n{str(error)}")

    def handle_profile_tab_change(self, index):
        """Handles actions when switching between profile tabs (e.g., A2DP, OPP), and refreshes the selected tab's UI.

        Args:
            index: The index of the newly selected tab in the device tab widget.
        """
        if hasattr(self, "playback_timer") and self.playback_timer is not None:
            if self.playback_timer.isActive():
                self.playback_timer.stop()
            self.playback_timer.deleteLater()
            self.playback_timer = None

        if not hasattr(self, 'device_tab_widget') or index < 0:
            return

        selected_tab = self.device_tab_widget.tabText(index)
        current_device = getattr(self, "device_address", None)

        if not current_device:
            self.log.warning("No active device set for tab switch")
            return

        self.log.info("Switched to %s tab for %s", selected_tab, current_device)

        if selected_tab == "A2DP":
            a2dp_panel = self.create_a2dp_profile_ui(current_device)
            self.refresh_tab(self.a2dp_tab_placeholder, a2dp_panel)
            self.log.info("Refreshed A2DP tab for %s", current_device)

        elif selected_tab == "OPP":
            opp_panel = self.create_opp_profile_ui(current_device)
            self.refresh_tab(self.opp_tab_placeholder, opp_panel)
            self.log.info("Refreshed OPP tab for %s", current_device)

        elif selected_tab == "HFP":
            hfp_panel = self.create_hfp_profile_ui(current_device)
            self.refresh_tab(self.hfp_tab_placeholder, hfp_panel)
            self.log.info("Refreshed HFP tab for %s", current_device)

    def load_device_profile_tabs(self, device_address, profile_list):
        """Loads and displays profile-related UI tabs for a specific Bluetooth device.

        Args:
            device_address: The Bluetooth address of the device.
            profile_list: A list of supported profile names.
                          The keyword 'all' will include all supported profiles.
        """
        self.clear_profile_ui()
        bold_font = QFont()
        bold_font.setBold(True)
        self.device_address = device_address
        is_connected = self.bluetooth_device_manager.is_device_connected(device_address)
        session_path = self.device_states.get(device_address, {}).get("session_path")
        if not is_connected and not session_path:
            warning_label = QLabel("Device is not connected. Connect to enable profile controls.")
            warning_label.setObjectName("WarningLabel")
            warning_label.setFont(bold_font)
            warning_label.setStyleSheet(styles.color_style_sheet)
            self.clear_layout(self.profile_methods_layout)
            self.profile_methods_layout.addWidget(warning_label)
            self.add_device_connection_controls(self.profile_methods_layout, device_address)
            return
        self.device_tab_widget = QTabWidget()
        self.device_tab_widget.setMaximumWidth(600)
        self.device_tab_widget.setFont(bold_font)
        self.device_tab_widget.setStyleSheet(styles.device_tab_widget_style_sheet)
        self.a2dp_tab_placeholder = QWidget()
        self.opp_tab_placeholder = QWidget()
        self.hfp_tab_placeholder = QWidget()
        added_profile_tabs = []
        profile_list = [p.lower() for p in profile_list]
        if 'a2dp' in profile_list or 'all' in profile_list:
            index = self.device_tab_widget.count()
            self.device_tab_widget.addTab(self.a2dp_tab_placeholder, "A2DP")
            added_profile_tabs.append(index)
        if 'opp' in profile_list or 'all' in profile_list:
            index = self.device_tab_widget.count()
            self.device_tab_widget.addTab(self.opp_tab_placeholder, "OPP")
            added_profile_tabs.append(index)
        if 'hfp' in profile_list or 'all' in profile_list:
            index = self.device_tab_widget.count()
            self.device_tab_widget.addTab(self.hfp_tab_placeholder, "HFP")
            added_profile_tabs.append(index)

        self.device_tab_widget.currentChanged.connect(self.handle_profile_tab_change)
        self.clear_layout(self.profile_methods_layout)
        self.profile_methods_layout.addWidget(self.device_tab_widget)
        if added_profile_tabs:
            self.device_tab_widget.setCurrentIndex(added_profile_tabs[0])
            self.handle_profile_tab_change(added_profile_tabs[0])
        self.add_device_connection_controls(self.profile_methods_layout, device_address)

    def add_device_connection_controls(self, layout, device_address):
        """Adds Connect, Disconnect, and Unpair buttons to the provided layout for the specified device.

        Args:
            layout: The layout to which the control buttons will be added.
            device_address: The Bluetooth address of the device the controls apply to.
        """
        bold_font = QFont()
        bold_font.setBold(True)
        button_layout = QHBoxLayout()
        self.is_connected = self.bluetooth_device_manager.is_device_connected(device_address)
        opp_connected = "OPP" in self.device_profiles.get(device_address, [])
        has_session = self.device_states.get(device_address, {}).get("session_path") is not None
        self.is_paired = device_address in self.bluetooth_device_manager.get_paired_devices()
        self.connect_button = QPushButton("Connect")
        self.connect_button.setFont(bold_font)
        self.connect_button.setStyleSheet(styles.bluetooth_profiles_button_style)
        self.connect_button.setFixedWidth(100)
        self.connect_button.setEnabled(not self.is_connected and not (opp_connected and has_session))
        self.connect_button.clicked.connect(
            lambda: self.perform_device_action('connect', device_address, load_profiles=True))
        button_layout.addWidget(self.connect_button)
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.setFont(bold_font)
        self.disconnect_button.setStyleSheet(styles.bluetooth_profiles_button_style)
        self.disconnect_button.setFixedWidth(100)
        self.disconnect_button.setEnabled(self.is_connected or (opp_connected and has_session))
        self.disconnect_button.clicked.connect(
            lambda: self.perform_device_action('disconnect', device_address, load_profiles=True))
        button_layout.addWidget(self.disconnect_button)
        self.unpair_button = QPushButton("Unpair")
        self.unpair_button.setFont(bold_font)
        self.unpair_button.setStyleSheet(styles.bluetooth_profiles_button_style)
        self.unpair_button.setFixedWidth(100)
        self.unpair_button.setEnabled(True)
        self.unpair_button.clicked.connect(
            lambda: self.perform_device_action('unpair', device_address, load_profiles=True))
        button_layout.addWidget(self.unpair_button)
        layout.addLayout(button_layout)

    def perform_device_action(self, action, device_address, load_profiles, opp_success=None):
        """Performs a Bluetooth device action and updates the UI.

        Args:
            action: One of 'pair','connect','disconnect', or 'unpair'.
            device_address: The Bluetooth address of the device.
            load_profiles: If True, refreshes the profile tabs after the action. If False, skips refreshing the profile tabs.
        """
        self.log.info("perform_device_action called with action=%s, load_profiles=%s", action, load_profiles)
        if action == 'pair':
            self.log.info("Attempting to pair with %s", device_address)
            if self.bluetooth_device_manager.is_device_paired(device_address):
                QMessageBox.information(self, "Already Paired", f"{device_address} is already paired.")
                self.add_paired_device_to_list(device_address)
                return
            success = self.bluetooth_device_manager.pair(device_address)
        elif action == 'connect':
            dialog = QDialog(self)
            dialog.setWindowTitle("Select Bluetooth Profiles to Connect")
            dialog.setMinimumSize(400, 400)
            dialog.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            dialog.setModal(True)
            layout = QVBoxLayout(dialog)
            layout.setContentsMargins(15, 15, 15, 15)
            layout.setSpacing(5)
            all_profiles = QCheckBox("All Profiles")
            a2dp_checkbox = QCheckBox("A2DP (Audio Streaming)")
            opp_checkbox = QCheckBox("OPP (File Transfer)")
            hfp_checkbox = QCheckBox("HFP (Telephony)")
            layout.addWidget(all_profiles)
            layout.addWidget(a2dp_checkbox)
            layout.addWidget(opp_checkbox)
            layout.addWidget(hfp_checkbox)
            a2dp_role_group = QGroupBox("Select A2DP Role")
            role_layout = QHBoxLayout()
            sink_radio = QRadioButton("Sink")
            source_radio = QRadioButton("Source")
            sink_radio.setChecked(True)
            role_layout.addWidget(sink_radio)
            role_layout.addWidget(source_radio)
            a2dp_role_group.setLayout(role_layout)
            a2dp_role_group.setVisible(False)
            layout.addWidget(a2dp_role_group)
            a2dp_checkbox.stateChanged.connect(lambda: a2dp_role_group.setVisible(a2dp_checkbox.isChecked()))
            #hfp_role_group = QGroupBox("Select HFP Role")
            #hfp_role_layout = QHBoxLayout()
            #ag_radio = QRadioButton("Audio Gateway (AG)")
            #hf_radio = QRadioButton("Hands-Free (HF)")
            #ag_radio.setChecked(True)
            #hfp_role_layout.addWidget(ag_radio)
            #hfp_role_layout.addWidget(hf_radio)
            #hfp_role_group.setLayout(hfp_role_layout)
            #hfp_role_group.setVisible(False)
            #layout.addWidget(hfp_role_group)
            #hfp_checkbox.stateChanged.connect(lambda: hfp_role_group.setVisible(hfp_checkbox.isChecked()))
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
            layout.addWidget(buttons)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            if dialog.exec():
                self.selected_profiles.clear()
                if all_profiles.isChecked():
                    self.selected_profiles['all'] = True
                if a2dp_checkbox.isChecked():
                    self.selected_profiles['a2dp'] = 'sink' if sink_radio.isChecked() else 'source'
                if opp_checkbox.isChecked():
                    self.selected_profiles['opp'] = True
                if hfp_checkbox.isChecked():
                    #self.selected_profiles['hfp'] = 'ag' if ag_radio.isChecked() else 'hf'
                    self.selected_profiles['hfp'] = True
                if not self.selected_profiles:
                    QMessageBox.warning(self, "No Profile Selected", "Please select at least one profile to connect.")
                    return
                self.device_profiles[device_address] = []
                failed_profiles = []
                errors = {}
                all_success = True
                for profile, role in self.selected_profiles.items():
                    success = False
                    if profile == 'all':
                        success = self.bluetooth_device_manager.connect(device_address)
                        if success:
                            connected_uuids = self.bluetooth_device_manager.get_connected_profile_uuids(device_address)
                            if (
                                    constants.profile_uuids["A2DP Sink"] in connected_uuids or constants.profile_uuids["A2DP Source"] in connected_uuids):
                                self.device_profiles[device_address].append("A2DP")
                            else:
                                failed_profiles.append("A2DP")
                                all_success = False
                            if constants.profile_uuids["OPP"] in connected_uuids:
                                session_path = self.bluetooth_device_manager.create_obex_session(device_address, "opp")
                                if session_path:
                                    self.device_profiles[device_address].append("OPP")
                                    self.device_states.setdefault(device_address, {})["session_path"] = session_path
                                else:
                                    failed_profiles.append("OPP")
                                    all_success = False
                            if constants.profile_uuids["HFP AG"] in connected_uuids:
                                self.device_profiles[device_address].append("HFP")
                            else:
                                failed_profiles.append("HFP")
                                all_success = False
                        else:
                            failed_profiles.extend(["A2DP", "OPP"])
                            all_success = False
                    elif profile == 'a2dp':
                        uuid = constants.profile_uuids["A2DP Sink"] if role == 'sink' else constants.profile_uuids["A2DP Source"]
                        success = self.bluetooth_device_manager.connect_profile(device_address, profile_uuid=uuid)
                        if success:
                            self.device_profiles[device_address].append("A2DP")
                        else:
                            failed_profiles.append("A2DP")
                            all_success = False
                    elif profile == 'opp':
                        session_path = self.bluetooth_device_manager.create_obex_session(device_address, "opp")
                        if session_path:
                            self.device_profiles[device_address].append("OPP")
                            self.device_states.setdefault(device_address, {})["session_path"] = session_path
                            success = True
                        else:
                            failed_profiles.append("OPP")
                            all_success = False
                    elif profile == "hfp":
                        uuid = constants.profile_uuids["HFP AG"]
                        success = self.bluetooth_device_manager.connect_profile(device_address, profile_uuid=uuid)
                        if success:
                            self.device_profiles[device_address].append("HFP")
                        else:
                            failed_profiles.append("HFP")
                            all_success = False

                if all_success:
                    QMessageBox.information(self, "Connection Successful",
                                            f"Connected profiles: {', '.join(self.device_profiles[device_address])}")
                else:
                    message = ""
                    if self.device_profiles[device_address]:
                        message += f"Successfully connected: {', '.join(self.device_profiles[device_address])}\n"
                    if failed_profiles:
                        message += "Failed to connect:\n"
                        for profile in failed_profiles:
                            error_message = errors.get(profile.lower(), "Unknown error")
                            message += f" - {profile}: {error_message}\n"
                    QMessageBox.warning(self, "Connection Result", message.strip())
                if load_profiles and self.device_profiles.get(device_address):
                    self.clear_device_discovery_results()
                    self.clear_profile_ui()
                    self.load_device_profile_tabs(device_address, self.device_profiles[device_address])
        elif action == 'disconnect':
            state = self.device_states.get(device_address, {})
            session_path = state.get("session_path")
            opp_connected = "OPP" in self.device_profiles.get(device_address, [])
            a2dp_connected = "A2DP" in self.device_profiles.get(device_address, [])
            hfp_connected = "HFP" in self.device_address.get(device_address, [])
            bluetooth_connected = self.bluetooth_device_manager.is_device_connected(device_address)
            bt_success = True

            if opp_connected and session_path:
                self.bluetooth_device_manager.remove_obex_session(session_path)
                state["session_path"] = None
                self.device_states[device_address] = state

            if a2dp_connected or bluetooth_connected:
                bt_success = self.bluetooth_device_manager.disconnect(device_address)

            if hfp_connected or bluetooth_connected:
                bt_success = self.bluetooth_device_manager.disconnect(device_address)
            if bt_success:
                QMessageBox.information(self, "Disconnection Successful", f"{device_address} was disconnected.")
                self.log.info("Disconnected from %s", device_address)
            else:
                QMessageBox.warning(self, "Disconnection Failed", f"Could not disconnect from {device_address}")
                self.log.warning(f"Disconnection failed: OPP={opp_success}, BT={bt_success}")

            self.device_profiles.pop(device_address, None)
            self.device_states.pop(device_address, None)
            self.clear_profile_ui()
            self.load_device_profile_tabs(device_address, [])
            self.selected_profiles = {}
        elif action == 'unpair':
            success = self.bluetooth_device_manager.unpair_device(device_address)
            if success:
                self.log.info("Unpaired %s", device_address)
            else:
                QMessageBox.warning(self, "Unpair Failed", f"Could not unpair {device_address}")
            self.device_profiles.pop(device_address, None)
            self.clear_profile_ui()
            self.remove_device_from_list(device_address)
            if self.profiles_list_widget.count() == 1:
                self.profiles_list_widget.itemSelectionChanged.connect(self.handle_profile_selection)
            else:
                self.load_device_profile_tabs(device_address, [])
        else:
            self.log.error("Unknown action: %s", action)

    def remove_device_from_list(self, unpaired_device_address):
        """Removes a specific unpaired device from the profiles list (if present).

        Args:
            unpaired_device_address: Bluetooth address of the unpaired device.
        """
        for i in range(self.profiles_list_widget.count()):
            item_text = self.profiles_list_widget.item(i).text().strip()
            if item_text == unpaired_device_address:
                self.profiles_list_widget.takeItem(i)
                break
        if self.profiles_list_widget.count() == 1:
            self.profiles_list_widget.itemSelectionChanged.connect(self.handle_profile_selection)
        else:
            self.load_device_profile_tabs(unpaired_device_address)

    def register_bluetooth_agent(self):
        """Register bluetooth pairing agent"""
        self.selected_capability = self.capability_combobox.currentText()
        self.log.info("Attempting to register agent with capability:%s", self.selected_capability)
        try:
            self.bluetooth_device_manager.register_agent(capability=self.selected_capability, ui_callback = self.handle_pairing_request)
            QMessageBox.information(self, "Agent Registered", f"Agent registered with capability: {self.selected_capability}")
        except Exception as error:
            self.log.info("Failed to register agent:%s", error)
            QMessageBox.critical(self, "Registration Failed", f"Could not register agent.\n{error}")

    def unregister_bluetooth_agent(self):
        """Unregister bluetooth pairing agent."""
        self.log.info("Attempting to unregister the Bluetooth agent...")
        try:
            self.bluetooth_device_manager.unregister_agent()
            QMessageBox.information(self, "Agent Unregistered", "Bluetooth agent was successfully unregistered.")
        except Exception as error:
            self.log.error("Failed to unregister agent: %s", error)
            QMessageBox.critical(self, "Unregistration Failed", f"Could not unregister agent.")

    def handle_pairing_request(self, request_type, device, uuid=None, passkey=None):
        """Handle various incoming Bluetooth pairing requests and user interactions.

        Args:
            request_type: The type of pairing request.
            device: The D-Bus object path of the Bluetooth device.
            uuid: The UUID of the Bluetooth service or PIN to display.
            passkey: The passkey for confirmation or display.

        Returns:
            PIN , Passkey, True, or None based on request type and user interaction.
        """
        self.log.info(f"Handling pairing request: {request_type} for {device}")
        device_address = device.split("dev_")[-1].replace("_", ":")
        handler_name = constants.pairing_request_handlers.get(request_type)
        if not handler_name:
            self.log.warning(f"Unknown pairing request type: {request_type}")
            return None
        handler = getattr(self, handler_name)
        return handler(device_address, uuid, passkey)

    def handle_pin_request(self, device_address, uuid=None, passkey=None):
        """Handle PIN code input from the user for pairing.

        Args:
            device_address: The address of the Bluetooth device.
            uuid: The UUID of the Bluetooth service or PIN to display.
            passkey: The passkey for confirmation or display.

        Returns:
             PIN entered by the user.
        """
        pin, user_response = QInputDialog.getText(self, "Pairing Request", f"Enter PIN for device {device_address}:")
        if user_response and pin:
            return pin
        self.log.info("User cancelled or provided no PIN for device %s", device_address)

    def handle_passkey_request(self, device_address, uuid=None, passkey=None):
        """Handle passkey input from the user for pairing.

        Args:
            device_address: The address of the Bluetooth device.
            uuid: The UUID of the Bluetooth service or PIN to display.
            passkey: The passkey for confirmation or display.

        Returns:
            The passkey entered by the user, or False if cancelled.
        """
        passkey_value, user_response = QInputDialog.getInt(self, "Pairing Request", f"Enter passkey for device {device_address}:")
        if not user_response:
            self.log.info("User cancelled passkey input for device %s", device_address)
            return False
        return passkey_value

    def handle_confirm_request(self, device_address, uuid=None, passkey=None):
        """Handle passkey confirmation dialog for pairing.

        Args:
            device_address: The address of the Bluetooth device.
            uuid: The UUID of the Bluetooth service or PIN to display.
            passkey: The passkey for confirmation or display.

        Returns:
            True if user confirms, False otherwise.
        """
        reply = QMessageBox.question(self, "Confirm Pairing", f"Device {device_address} requests to pair with passkey: {uuid}\nAccept?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            return True
        self.log.info("User rejected pairing confirmation request")
        return False

    def handle_authorize_request(self, device_address, uuid=None, passkey=None):
        """Handle authorization request for allowing a Bluetooth service.

        Args:
            device_address: The address of the Bluetooth device.
            uuid: The UUID of the Bluetooth service or PIN to display.
            passkey: The passkey for confirmation or display.

        Returns:
            True if user authorizes, False if denied.
        """
        reply = QMessageBox.question(self, "Authorize Service",
            f"Device {device_address} wants to use service {uuid}\nAllow?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            QMessageBox.information(self, "Connection Successful", f"{device_address} was connected.")
            return True
        self.log.warning("User denied service authorization for device %s", device_address)
        return False

    def display_pin_or_passkey(self, device_address, value, label):
        """Display a PIN or passkey to the user for manual entry on the Bluetooth device.

        Args:
            device_address: The address of the Bluetooth device.
            value: The PIN or passkey value to display.
            label: The label to display ('PIN' or 'Passkey').
        """
        if value is None:
            self.log.warning(f"{label} requested but no value provided for device {device_address}.")
            return
        QMessageBox.information(self, f"Display {label}", f"Enter this {label.lower()} on {device_address}: {value}")

    def handle_display_pin_request(self, device_address, uuid=None, passkey=None):
        """Handle display PIN request during pairing.

        Args:
            device_address : The address of the Bluetooth device.
            uuid: The UUID of the Bluetooth service or PIN to display.
            passkey: The passkey for confirmation or display.
        """
        self.display_pin_or_passkey(device_address, uuid, "PIN")

    def handle_display_passkey_request(self, device_address, uuid=None, passkey=None):
        """Handle display passkey request during pairing.

        Args:
            device_address: The address of the Bluetooth device.
            uuid: The UUID of the Bluetooth service or PIN to display.
            passkey: The passkey for confirmation or display.
        """
        self.display_pin_or_passkey(device_address, passkey, "Passkey")

    def handle_cancel_request(self, device_address, uuid=None, passkey=None):
        """Handle cancellation of the pairing process.

        Args:
            device_address : The address of the Bluetooth device.
            uuid: The UUID of the Bluetooth service or PIN to display.
            passkey: The passkey for confirmation or display.
        """
        QMessageBox.warning(self, "Pairing Cancelled", f"Pairing with {device_address} was cancelled.")

    def initialize_host_ui(self):
        """Create and display the main testing application GUI."""
        self.main_grid_layout = QGridLayout()
        bold_font = QFont()
        bold_font.setBold(True)
        # Grid 1: GAP button,Paired_devices, Controller details
        self.gap_button = QPushButton("GAP")
        self.gap_button.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.gap_button.setStyleSheet(styles.gap_button_style_sheet)
        self.gap_button.setFixedWidth(350)
        self.gap_button.setMinimumHeight(30)
        self.gap_button.clicked.connect(lambda: self. handle_profile_selection("GAP "))
        self.main_grid_layout.addWidget(self.gap_button, 0, 0, 1, 2)
        self.profiles_list_widget = QListWidget()
        self.profiles_list_widget.setFont(bold_font)
        self.profiles_list_widget.setContentsMargins(4, 4, 4, 4)
        self.profiles_list_widget.setStyleSheet(styles.profiles_list_style_sheet)
        self.profiles_list_widget.setFixedWidth(350)
        self.profiles_list_widget.itemClicked.connect(lambda: self.handle_profile_selection())
        paired_devices_label = QLabel("Paired Devices")
        paired_devices_label.setObjectName("PairedDevicesList")
        paired_devices_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        paired_devices_label.setStyleSheet(styles.color_style_sheet)
        paired_devices_layout = QVBoxLayout()
        paired_devices_layout.setContentsMargins(8, 8, 8, 8)
        paired_devices_layout.setSpacing(6)
        paired_devices_layout.addWidget(paired_devices_label)
        paired_devices_layout.addWidget(self.profiles_list_widget)
        paired_devices_widget = QWidget()
        paired_devices_widget.setLayout(paired_devices_layout)
        paired_devices_widget.setFixedWidth(350)
        paired_devices_widget.setStyleSheet(styles.panel_style_sheet)
        self.main_grid_layout.addWidget(paired_devices_widget, 1, 0, 4, 2)
        controller_details_widget = QWidget()
        controller_layout = QVBoxLayout(controller_details_widget)
        controller_details_widget.setFixedWidth(350)
        controller_details_widget.setStyleSheet(styles.panel_style_sheet)
        controller_label = QLabel("Controller Details")
        controller_label.setObjectName("ControllerDetails")
        controller_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        controller_label.setStyleSheet(styles.color_style_sheet)
        controller_layout.addWidget(controller_label)
        details = get_controller_interface_details(self.log, interface=self.interface, detail_level='extended_info')
        self.grid = QGridLayout()
        self.grid.setHorizontalSpacing(10)
        self.grid.setVerticalSpacing(12)
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 2)
        self.add_controller_details_row(0, "Controller Name", details.get("Name", "N/A"))
        self.add_controller_details_row(1, "Controller Address", details.get("BD_ADDR", "N/A"))
        self.add_controller_details_row(2, "Link Mode", details.get("Link mode", "N/A"))
        self.add_controller_details_row(3, "Link Policy", details.get("Link policy", "N/A"))
        self.add_controller_details_row(4, "HCI Version", details.get("HCI Version", "N/A"))
        self.add_controller_details_row(5, "LMP Version", details.get("LMP Version", "N/A"))
        self.add_controller_details_row(6, "Manufacturer", details.get("Manufacturer", "N/A"))
        controller_layout.addLayout(self.grid)
        self.main_grid_layout.addWidget(controller_details_widget, 5, 0, 8, 2)
        # Grid2: Profile description
        profile_description_label = QLabel("Profile Methods or Procedures:")
        profile_description_label.setObjectName("profile_description_label")
        profile_description_label.setFont(bold_font)
        profile_description_label.setStyleSheet(styles.color_style_sheet)
        self.main_grid_layout.addWidget(profile_description_label, 0, 2)
        self.profile_methods_layout = QVBoxLayout()
        self.profile_methods_widget = QWidget()
        self.profile_methods_widget.setObjectName("ProfileContainer")
        self.profile_methods_widget.setStyleSheet(styles.middle_panel_style_sheet)
        self.profile_methods_widget.setMinimumWidth(350)
        self.profile_methods_widget.setMaximumWidth(500)
        self.profile_methods_widget.setLayout(self.profile_methods_layout)
        self.main_grid_layout.addWidget(self.profile_methods_widget, 1, 2, 12, 2)
        back_button = QPushButton("Back")
        back_button.setFixedSize(100, 40)
        back_button.setStyleSheet(styles.back_button_style_sheet)
        back_button.clicked.connect(lambda: self.back_callback())
        back_layout = QHBoxLayout()
        back_layout.addWidget(back_button)
        back_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.main_grid_layout.addLayout(back_layout, 999, 5)
        self.main_grid_layout.setColumnStretch(0, 0)
        self.main_grid_layout.setColumnStretch(1, 0)
        self.main_grid_layout.setColumnStretch(2, 1)
        self.setLayout(self.main_grid_layout)
        self.load_paired_devices()
        self.setup_logs_section()

    def setup_logs_section(self):
        """Initializes the dump logs tab section with log viewers for Bluetoothd, Pulseaudio, HCI Dump, Obexd, and Ofonod."""
        bold_font = QFont()
        bold_font.setBold(True)

        dump_logs_label = QLabel("Dump Logs:")
        dump_logs_label.setFont(bold_font)
        dump_logs_label.setStyleSheet(styles.color_style_sheet)
        self.main_grid_layout.addWidget(dump_logs_label, 0, 4)

        self.dump_logs_text_browser = QTabWidget()
        self.dump_logs_text_browser.setFixedWidth(400)
        self.dump_logs_text_browser.setStyleSheet(styles.tab_style_sheet)
        self.dump_logs_text_browser.setUsesScrollButtons(True)
        self.main_grid_layout.addWidget(self.dump_logs_text_browser, 1, 4, 12, 2)

        self.setup_bluetoothd_log()
        self.setup_pulseaudio_log()
        self.setup_hcidump_log()
        self.setup_obexd_log()
        self.setup_ofonod_log()

    def setup_bluetoothd_log(self):
        """Sets up the Bluetoothd log viewer tab and connects it to the log file for live updates."""
        normal_font = QFont()
        normal_font.setBold(False)

        self.bluetoothd_log_text_browser = QTextEdit()
        self.bluetoothd_log_text_browser.setFont(normal_font)
        self.bluetoothd_log_text_browser.setMinimumWidth(50)
        self.bluetoothd_log_text_browser.setReadOnly(True)
        self.bluetoothd_log_text_browser.setStyleSheet(styles.transparent_textedit_style)

        self.dump_logs_text_browser.addTab(self.bluetoothd_log_text_browser, "Bluetoothd_Logs")

        self.bluetoothd_log_file_fd = open(self.bluetoothd_log_file_path, "r")
        if self.bluetoothd_log_file_fd:
            content = self.bluetoothd_log_file_fd.read()
            self.bluetoothd_log_text_browser.append(content)
            self.bluetoothd_file_position = self.bluetoothd_log_file_fd.tell()

        self.bluetoothd_file_watcher = QFileSystemWatcher()
        self.bluetoothd_file_watcher.addPath(self.bluetoothd_log_file_path)
        self.bluetoothd_file_watcher.fileChanged.connect(self.update_bluetoothd_log)

    def setup_pulseaudio_log(self):
        """Sets up the Pulseaudio log viewer tab and connects it to the log file for live updates."""
        normal_font = QFont()
        normal_font.setBold(False)

        self.pulseaudio_log_text_browser = QTextEdit()
        self.pulseaudio_log_text_browser.setFont(normal_font)
        self.pulseaudio_log_text_browser.setMinimumWidth(50)
        self.pulseaudio_log_text_browser.setReadOnly(True)
        self.pulseaudio_log_text_browser.setStyleSheet(styles.transparent_textedit_style)

        self.dump_logs_text_browser.addTab(self.pulseaudio_log_text_browser, "Pulseaudio_Logs")

        self.pulseaudio_log_file_fd = open(self.pulseaudio_log_file_path, "r")
        if self.pulseaudio_log_file_fd:
            content = self.pulseaudio_log_file_fd.read()
            self.pulseaudio_log_text_browser.append(content)
            self.pulseaudio_file_position = self.pulseaudio_log_file_fd.tell()

        self.pulseaudio_file_watcher = QFileSystemWatcher()
        self.pulseaudio_file_watcher.addPath(self.pulseaudio_log_file_path)
        self.pulseaudio_file_watcher.fileChanged.connect(self.update_pulseaudio_log)

    def setup_hcidump_log(self):
        """Sets up the Hcidump log viewer tab and connects it to the log file for live updates."""
        normal_font = QFont()
        normal_font.setBold(False)

        self.hci_dump_log_text_browser = QTextEdit()
        self.hci_dump_log_text_browser.setFont(normal_font)
        self.hci_dump_log_text_browser.setMinimumWidth(50)
        self.hci_dump_log_text_browser.setReadOnly(True)
        self.hci_dump_log_text_browser.setStyleSheet(styles.transparent_textedit_style)

        self.dump_logs_text_browser.addTab(self.hci_dump_log_text_browser, "HCI_Dump_Logs")

        self.hci_log_file_fd = open(self.hcidump_log_name, "r")
        if self.hci_log_file_fd:
            content = self.hci_log_file_fd.read()
            self.hci_dump_log_text_browser.append(content)
            self.hci_file_position = self.hci_log_file_fd.tell()

        self.hci_file_watcher = QFileSystemWatcher()
        self.hci_file_watcher.addPath(self.hcidump_log_name)
        self.hci_file_watcher.fileChanged.connect(self.update_hci_log)

    def setup_obexd_log(self):
        """Sets up the Obexd log viewer tab and connects it to the log file for live updates."""
        normal_font = QFont()
        normal_font.setBold(False)

        self.obexd_log_text_browser = QTextEdit()
        self.obexd_log_text_browser.setFont(normal_font)
        self.obexd_log_text_browser.setMinimumWidth(50)
        self.obexd_log_text_browser.setReadOnly(True)
        self.obexd_log_text_browser.setStyleSheet(styles.transparent_textedit_style)

        self.dump_logs_text_browser.addTab(self.obexd_log_text_browser, "Obexd_Logs")

        self.obexd_log_file_fd = open(self.obexd_log_file_path, "r")
        if self.obexd_log_file_fd:
            content = self.obexd_log_file_fd.read()
            self.obexd_log_text_browser.append(content)
            self.obexd_file_position = self.obexd_log_file_fd.tell()

        self.obexd_file_watcher = QFileSystemWatcher()
        self.obexd_file_watcher.addPath(self.obexd_log_file_path)
        self.obexd_file_watcher.fileChanged.connect(self.update_obexd_log)

    def setup_ofonod_log(self):
        """Sets up the Ofonod log viewer tab and connects it to the log file for live updates."""
        normal_font = QFont()
        normal_font.setBold(False)

        self.ofonod_log_text_browser = QTextEdit()
        self.ofonod_log_text_browser.setFont(normal_font)
        self.ofonod_log_text_browser.setMinimumWidth(50)
        self.ofonod_log_text_browser.setReadOnly(True)
        self.ofonod_log_text_browser.setStyleSheet(styles.transparent_textedit_style)

        self.dump_logs_text_browser.addTab(self.ofonod_log_text_browser, "Ofonod_Logs")

        self.ofonod_log_file_fd = open(self.ofonod_log_file_path, "r")
        if self.ofonod_log_file_fd:
            content = self.ofonod_log_file_fd.read()
            self.ofonod_log_text_browser.append(content)
            self.ofonod_file_position = self.ofonod_log_file_fd.tell()

        self.ofonod_file_watcher = QFileSystemWatcher()
        self.ofonod_file_watcher.addPath(self.ofonod_log_file_path)
        self.ofonod_file_watcher.fileChanged.connect(self.update_ofonod_log)

    def update_bluetoothd_log(self):
        """Updates the bluetoothd log display with new log entries.
        Reads the bluetoothd log file from the last known position and appends the new content to bluetoothd
        log text browser."""
        if self.bluetoothd_log_file_fd:
            self.bluetoothd_log_file_fd.seek(self.bluetoothd_file_position)
            content = self.bluetoothd_log_file_fd.read()
            self.bluetoothd_file_position = self.bluetoothd_log_file_fd.tell()
            self.bluetoothd_log_text_browser.append(content)

    def update_pulseaudio_log(self):
        """Updates the pulseaudio log display with new log entries.
        Reads the pulseaudio log file from the last known position and appends the new content to pulseaudio
        log text browser."""
        if self.pulseaudio_log_file_fd:
            self.pulseaudio_log_file_fd.seek(self.pulseaudio_file_position)
            content = self.pulseaudio_log_file_fd.read()
            self.pulseaudio_file_position = self.pulseaudio_log_file_fd.tell()
            self.pulseaudio_log_text_browser.append(content)

    def update_hci_log(self):
        """Updates the hcidump log display with new log entries.
        Reads the hci log file from the last known position and appends the new content to hci dump
        log text browser."""
        if self.hci_log_file_fd:
            self.hci_log_file_fd.seek(self.hci_file_position)
            content = self.hci_log_file_fd.read()
            self.hci_file_position = self.hci_log_file_fd.tell()
            self.hci_dump_log_text_browser.append(content)

    def update_obexd_log(self):
        """Updates the obexd log display with new log entries.
        Reads the obexd log file from the last known position and appends the new content to obexd
        log text browser."""
        if self.obexd_log_file_fd:
            self.obexd_log_file_fd.seek(self.obexd_file_position)
            content = self.obexd_log_file_fd.read()
            self.obexd_file_position = self.obexd_log_file_fd.tell()
            self.obexd_log_text_browser.append(content)

    def update_ofonod_log(self):
        """Updates the ofonod log display with new log entries.
        Reads the ofonod log file from the last known position and appends the new content to ofonod
        log text browser."""
        if self.ofonod_log_file_fd:
            self.ofonod_log_file_fd.seek(self.ofonod_file_position)
            content = self.ofonod_log_file_fd.read()
            self.ofonod_file_position = self.ofonod_log_file_fd.tell()
            self.ofonod_log_text_browser.append(content)

    def prompt_file_transfer_confirmation(self, file_path):
        """Prompt user to confirm a file transfer and return their decision.

        Args:
            file_path: The full path of the incoming file.
        """
        file_name = os.path.basename(file_path)
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Incoming File")
        msg_box.setText(f"Accept incoming file?\n\n{file_name}")
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setIcon(QMessageBox.Icon.Question)
        result = msg_box.exec()
        return result == QMessageBox.StandardButton.Yes

    def clear_profile_ui(self):
        """Clears the profile UI by stopping any ongoing media playback timer,
        removing all widgets from the profile layout, and resetting all related
        widget references to None to prevent further access."""
        self.stop_media_playback_timer()
        # Clear layout
        self.clear_layout(self.profile_methods_layout)
        # Prevent access to deleted widgets
        self.device_tab_widget = None
        self.a2dp_tab_placeholder = None
        self.opp_tab_placeholder = None
        self.track_status_label = None
        self.song_title_label = None
        self.song_artist_label = None
        self.song_album_label = None
        self.progress_slider = None
        self.elapsed_time_label = None
        self.remaining_time_label = None

    def start_media_playback_timer(self):
        """Starts a timer that periodically updates media playback information every second."""
        if hasattr(self, "playback_timer") and self.playback_timer is not None:
            if self.playback_timer.isActive():
                self.playback_timer.stop()
            self.playback_timer.deleteLater()
        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self.media_player_info)
        self.playback_timer.start(1000)

    def stop_media_playback_timer(self):
        """Stops and deletes the media playback timer if it exists and is active."""
        if hasattr(self, "playback_timer") and self.playback_timer is not None:
            if self.playback_timer.isActive():
                self.playback_timer.stop()
            self.playback_timer.deleteLater()
            self.playback_timer = None

    def browse_audio_files(self):
        """Browse and add multiple audio files to playlist."""
        files, _ = QFileDialog.getOpenFileNames(caption="Select Audio File", filter="WAV files (*.wav)")
        invalid_files = []
        for file_path in files:
            if os.path.exists(file_path):
                self.audio_playlist.addItem(file_path)
            else:
                invalid_files.append(file_path)
        if invalid_files:
            warning_msg = "The following files were not found and were not added:\n" + "\n".join(invalid_files)
            QMessageBox.warning(self, "File Not Found", warning_msg)

    def volume_control(self):
        """Retrieves the current media volume from the sink device and updates the volume slider UI.
        If the volume is successfully retrieved, it sets the value of `sink_volume_slider`.
        """
        volume = self.bluetooth_device_manager.get_media_volume(self.device_address_sink)
        if volume is not None:
            self.sink_volume_slider.setValue(volume)

    def set_device_volume(self, value):
        """Sets the media volume on the sink device to the specified value.

        Args:
            value: The volume level to be set.
        """
        self.bluetooth_device_manager.set_media_volume(self.device_address_sink, value)

    def media_player_info(self):
        """Updates the media player UI with current playback information from the sink device.
        Displays track status, title, artist, album, and playback progress.
        If no information is available, resets the display to default 'unknown' values.
        """
        if not hasattr(self, "track_status_label") or self.track_status_label is None:
            self.log.warning("Track status label does not exist anymore. Skipping update.")
            return
        info = self.bluetooth_device_manager.get_media_playback_info(self.device_address_sink)
        if not info:
            self.track_status_label.setText("Status: Unknown")
            self.song_title_label.setText("Title: Unknown")
            self.song_artist_label.setText("Artist: -")
            self.song_album_label.setText("Album: -")
            self.progress_slider.setEnabled(False)
            self.progress_slider.setValue(0)
            self.elapsed_time_label.setText("00:00")
            self.remaining_time_label.setText("00:00")
            return
        status = info["status"]
        track = info["track"]
        position = info["position"] // 1000
        duration = info["duration"] // 1000
        title = track.get("title", "Unknown")
        artist = track.get("artist", "-")
        album = track.get("album", "-")
        try:
            self.track_status_label.setText(f"Status: {status}")
            self.song_title_label.setText(title)
            self.song_artist_label.setText(artist)
            self.song_album_label.setText(album)
            self.progress_slider.setEnabled(True)
            self.progress_slider.setMaximum(duration)
            self.progress_slider.setValue(position)
            elapsed_mins = position // 60
            elapsed_secs = position % 60
            remaining = duration - position
            remaining_mins = remaining // 60
            remaining_secs = remaining % 60
            self.elapsed_time_label.setText(f"{elapsed_mins:02}:{elapsed_secs:02}")
            self.remaining_time_label.setText(f"{remaining_mins:02}:{remaining_secs:02}")
        except RuntimeError as e:
            pass

    def remove_selected_file(self):
        """Removes the selected file from the audio playlist."""
        for item in self.audio_playlist.selectedItems():
            self.audio_playlist.takeItem(self.audio_playlist.row(item))

    def clear_playlist(self):
        """Clears all items from the audio playlist."""
        self.audio_playlist.clear()

    def set_source_volume(self, value):
        """Sets the media volume for the A2DP source device.

        Args:
            value: The volume level to set.
        """
        self.bluetooth_device_manager.set_media_volume(self.device_address_source, value)

    def refresh_tab(self, placeholder: QWidget, panel: QWidget):
        """Replaces the contents of a placeholder widget with the given panel.
        Clears existing layout and widgets, sets a new layout with the panel, and updates the UI.

        Args:
            placeholder: The container widget to refresh.
            panel: The new content widget.
        """
        old_layout = placeholder.layout()
        if old_layout is not None:
            while old_layout.count():
                child = old_layout.takeAt(0)
                if child.widget():
                    child.widget().setParent(None)
            QWidget().setLayout(old_layout)

        layout = QVBoxLayout()
        layout.addWidget(panel)
        placeholder.setLayout(layout)

        placeholder.repaint()
        placeholder.update()
        placeholder.updateGeometry()
        QCoreApplication.processEvents()

    def setup_pairing_status_listener(self):
        """Setups up the signal listener for changes in device pairing status."""
        self.bluetooth_device_manager.setup_pairing_signal_listener(self.handle_pairing_status_update)

    def handle_pairing_status_update(self, device_address, paired):
        """Handles updates to device's pairing status.

        Args:
            device_address: Bluetooth address of remote device.
            paired: Indicates whether pairing was successful or pairing failed.
        """
        if paired:
            self.log.info(f"Device paired: {device_address}")
            self.add_paired_device_to_list(device_address)
            QMessageBox.information(self, "Pairing Successful", f"{device_address} was paired successfully.")
        else:
            self.log.info(f"Pairing failed: {device_address}")
            QMessageBox.warning(self, "Pairing Failed", f"Pairing with {device_address} failed.")
            self.remove_device_from_list(device_address)

    '''def create_hfp_profile_ui(self, device_address):
        """Builds and returns the HFP (Hands-Free Profile) panel for call control."""
        bold_font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        hfp_label = QLabel("<b>HFP Functionality</b>")
        hfp_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        hfp_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(hfp_label)
        call_control_group = QGroupBox("Call Control")
        call_control_group.setStyleSheet(styles.bluetooth_profiles_groupbox_style)
        call_control_layout = QVBoxLayout()
        self.answer_call_button = QPushButton("Answer Call")
        self.hangup_call_button = QPushButton("Hang Up")
        self.dial_button = QPushButton("Dial Number")
        self.dial_last_button = QPushButton("Dial last number")
        self.phone_number_input = QLineEdit()
        self.phone_number_input.setPlaceholderText("Enter phone number")
        for button in [self.answer_call_button, self.hangup_call_button, self.dial_button, self.dial_last_button]:
            button.setStyleSheet(styles.bluetooth_profiles_button_style)
            button.setFont(bold_font)
        self.bluetooth_device_manager.setup_hfp_manager(device_address)
        self.dial_button.clicked.connect(lambda: self.bluetooth_device_manager.dial_number(device_address, self.phone_number_input.text()))
        self.answer_call_button.clicked.connect(lambda: self.bluetooth_device_manager.answer_call(device_address))
        self.hangup_call_button.clicked.connect(lambda: self.bluetooth_device_manager.hangup_active_call())
        self.dial_last_button.clicked.connect(lambda: self.bluetooth_device_manager.dial_last(device_address))
        call_control_layout.addWidget(self.phone_number_input)
        call_control_layout.addWidget(self.dial_button)
        call_control_layout.addWidget(self.answer_call_button)
        call_control_layout.addWidget(self.hangup_call_button)
        call_control_layout.addWidget(self.dial_last_button)
        call_control_group.setLayout(call_control_layout)
        layout.addWidget(call_control_group)
        layout.addStretch(1)
        widget = QWidget()
        widget.setLayout(layout)
        widget.setStyleSheet(styles.device_tab_widget_style_sheet)
        return widget'''

    '''def create_hfp_profile_ui(self, device_address):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        basic_layout = QVBoxLayout()
        self.phone_number_input = QLineEdit()
        self.phone_number_input.setPlaceholderText("Enter phone number")
        self.dial_button = QPushButton("Dial")
        self.answer_call_button = QPushButton("Answer")
        self.hangup_button = QPushButton("Hang Up")
        self.redial_button = QPushButton("Redial")
        #self.get_calls_button = QPushButton("Get Calls")
        for b in [self.dial_button, self.answer_call_button, self.hangup_button, self.redial_button]:
            b.setFixedHeight(15)
        basic_layout.addWidget(self.phone_number_input)
        for b in [self.dial_button, self.answer_call_button, self.hangup_button, self.redial_button]:
            basic_layout.addWidget(b)
        basic_group = self.create_hfp_sections("Basic Call Controls", basic_layout)
        advanced_layout = QVBoxLayout()
        for text in ["Get Calls", "Swap Calls", "Hold + Answer", "Release + Answer", "Private Chat"]:
            advanced_layout.addWidget(QPushButton(text))
        adv_group = self.create_hfp_sections("Advanced Call Handling", advanced_layout)
        audio_layout = QHBoxLayout()
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        audio_layout.addWidget(QLabel("Volume:"))
        audio_layout.addWidget(self.volume_slider)
        audio_group = self.create_hfp_sections("Audio Settings", audio_layout)
        dtmf_layout = QHBoxLayout()
        self.dtmf_input = QLineEdit()
        self.dtmf_input.setPlaceholderText("Enter DTMF tone (0–9, #, *)")
        self.dtmf_send_btn = QPushButton("Send")
        dtmf_layout.addWidget(self.dtmf_input)
        dtmf_layout.addWidget(self.dtmf_send_btn)
        dtmf_group = self.create_hfp_sections("DTMF Controls", dtmf_layout)
        layout.addWidget(basic_group)
        layout.addWidget(adv_group)
        layout.addWidget(audio_group)
        layout.addWidget(dtmf_group)
        self.bluetooth_device_manager.setup_hfp_manager(device_address)
        self.dial_button.clicked.connect(
            lambda: self.bluetooth_device_manager.dial_number(device_address, self.phone_number_input.text()))
        self.answer_call_button.clicked.connect(lambda: self.bluetooth_device_manager.answer_call(device_address))
        self.hangup_button.clicked.connect(lambda: self.bluetooth_device_manager.hangup_active_call())
        self.redial_button.clicked.connect(lambda: self.bluetooth_device_manager.dial_last(device_address))
        widget = QWidget()
        widget.setStyleSheet(styles.widget_style_sheet)
        widget.setLayout(layout)
        return widget

    def create_hfp_sections(self, title, inner_layout):
        group = QWidget()
        layout = QVBoxLayout(group)
        toggle = QToolButton(text=title, checkable=True, checked=False)
        toggle.setStyleSheet("QToolButton { font-weight: bold; }")
        toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        toggle.setArrowType(Qt.ArrowType.RightArrow)
        content = QWidget()
        content.setLayout(inner_layout)
        content.setVisible(False)
        toggle.toggled.connect(
            lambda checked: (
                content.setVisible(checked),
                toggle.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)
            )
        )
        layout.addWidget(toggle)
        layout.addWidget(content)
        return group'''

    def create_hfp_profile_ui(self, device_address):
        widget = QWidget()
        widget.setStyleSheet(styles.widget_style_sheet)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)

        self.phone_number_input = QLineEdit(widget)
        self.phone_number_input.setPlaceholderText("Enter phone number")

        self.dial_button = QPushButton("Dial", widget)
        self.answer_call_button = QPushButton("Answer", widget)
        self.hangup_button = QPushButton("Hang Up", widget)
        self.redial_button = QPushButton("Redial", widget)

        for b in [self.dial_button, self.answer_call_button, self.hangup_button, self.redial_button]:
            b.setFixedHeight(20)

        basic_layout = QVBoxLayout()
        basic_layout.addWidget(self.phone_number_input)
        for b in [self.dial_button, self.answer_call_button, self.hangup_button, self.redial_button]:
            basic_layout.addWidget(b)
        basic_group = self.create_hfp_sections("Basic Call Controls", basic_layout, parent=widget)

        adv_layout = QVBoxLayout()
        self.swap_calls_btn = QPushButton("Swap Calls", widget)
        self.hold_answer_btn = QPushButton("Hold + Answer", widget)
        self.release_answer_btn = QPushButton("Release + Answer", widget)
        self.private_chat_btn = QPushButton("Private Chat", widget)
        self.create_multiparty_btn = QPushButton("Create Multiparty", widget)
        self.hangup_multiparty_btn = QPushButton("Hangup Multiparty", widget)
        self.transfer_calls_btn = QPushButton("Transfer Calls", widget)
        self.dial_memory_btn = QPushButton("Dial Memory", widget)

        for b in [self.swap_calls_btn, self.hold_answer_btn, self.release_answer_btn,
                  self.private_chat_btn, self.create_multiparty_btn, self.hangup_multiparty_btn,
                  self.transfer_calls_btn, self.dial_memory_btn]:
            adv_layout.addWidget(b)
        adv_group = self.create_hfp_sections("Advanced Call Handling", adv_layout, parent=widget)

        audio_layout = QHBoxLayout()
        self.volume_slider = QSlider(Qt.Orientation.Horizontal, widget)
        self.volume_slider.setRange(0, 100)
        audio_layout.addWidget(QLabel("Volume:", widget))
        audio_layout.addWidget(self.volume_slider)
        audio_group = self.create_hfp_sections("Audio Settings", audio_layout, parent=widget)

        dtmf_layout = QHBoxLayout()
        self.dtmf_input = QLineEdit(widget)
        self.dtmf_input.setPlaceholderText("Enter DTMF tone (0–9, #, *)")
        self.dtmf_send_btn = QPushButton("Send", widget)
        dtmf_layout.addWidget(self.dtmf_input)
        dtmf_layout.addWidget(self.dtmf_send_btn)
        dtmf_group = self.create_hfp_sections("DTMF Controls", dtmf_layout, parent=widget)

        for group in [basic_group, adv_group, audio_group, dtmf_group]:
            layout.addWidget(group)

        self.bluetooth_device_manager.setup_hfp_manager(device_address)

        self.dial_button.clicked.connect(
            lambda: self.bluetooth_device_manager.dial_number(device_address, self.phone_number_input.text()))
        self.answer_call_button.clicked.connect(
            lambda: self.bluetooth_device_manager.answer_call(device_address))
        self.hangup_button.clicked.connect(
            lambda: self.bluetooth_device_manager.hangup_active_call())
        self.redial_button.clicked.connect(
            lambda: self.bluetooth_device_manager.dial_last(device_address))
        self.swap_calls_btn.clicked.connect(
            lambda: self.bluetooth_device_manager.release_and_swap(device_address))
        self.hold_answer_btn.clicked.connect(
            lambda: self.bluetooth_device_manager.hold_and_answer(device_address))
        self.release_answer_btn.clicked.connect(
            lambda: self.bluetooth_device_manager.release_and_answer(device_address))
        self.private_chat_btn.clicked.connect(
            lambda: self.bluetooth_device_manager.private_chat(
                device_address, self.bluetooth_device_manager.active_call_path))
        self.create_multiparty_btn.clicked.connect(
            lambda: self.bluetooth_device_manager.create_multiparty(device_address))
        self.hangup_multiparty_btn.clicked.connect(
            lambda: self.bluetooth_device_manager.hangup_multiparty(device_address))
        self.transfer_calls_btn.clicked.connect(
            lambda: self.bluetooth_device_manager.transfer_calls(device_address))
        self.dial_memory_btn.clicked.connect(
            lambda: self.bluetooth_device_manager.dial_memory(device_address,
                                                              memory_position=1))

        self.volume_slider.valueChanged.connect(
            lambda v: self.bluetooth_device_manager.set_call_volume(device_address, v))

        self.dtmf_send_btn.clicked.connect(
            lambda: self.bluetooth_device_manager.send_tones(device_address, self.dtmf_input.text()))

        return widget

    '''def create_hfp_sections(self, title, inner_layout, parent=None):
        """Create collapsible HFP section with smooth expand/collapse + fade animation and light blue theme."""
        container = QWidget(parent)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(2)

        toggle = QToolButton(container)
        toggle.setText(title)
        toggle.setCheckable(True)
        toggle.setChecked(False)
        toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        toggle.setArrowType(Qt.ArrowType.RightArrow)
        toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        toggle.setStyleSheet(styles.hfptoggle_stylesheet)
        content = QGroupBox(container)
        content.setLayout(inner_layout)
        content.setMaximumHeight(0)
        content.setWindowOpacity(0.0)
        content.setVisible(False)
        content.setStyleSheet(styles.content_stylesheet)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 2)
        content.setGraphicsEffect(shadow)

        height_anim = QPropertyAnimation(content, b"maximumHeight")
        height_anim.setDuration(250)
        height_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        fade_anim = QPropertyAnimation(content, b"windowOpacity")
        fade_anim.setDuration(250)
        fade_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        animation_group = QParallelAnimationGroup()
        animation_group.addAnimation(height_anim)
        animation_group.addAnimation(fade_anim)
        self.hfp_sections.append(toggle)

        def toggle_section(checked):
            content.setVisible(True)
            if checked:
                height_anim.setStartValue(0)
                height_anim.setEndValue(content.sizeHint().height())
                fade_anim.setStartValue(0.0)
                fade_anim.setEndValue(1.0)
                toggle.setArrowType(Qt.ArrowType.DownArrow)
            else:
                height_anim.setStartValue(content.height())
                height_anim.setEndValue(0)
                fade_anim.setStartValue(1.0)
                fade_anim.setEndValue(0.0)
                toggle.setArrowType(Qt.ArrowType.RightArrow)

                def hide_after():
                    content.setVisible(False)
                    animation_group.finished.disconnect(hide_after)

                animation_group.finished.connect(hide_after)

            animation_group.start()

        toggle.toggled.connect(toggle_section)

        container_layout.addWidget(toggle)
        container_layout.addWidget(content)
        return container'''

    def create_hfp_sections(self, title, inner_layout, parent=None):
        """Create collapsible HFP section with smooth expand/collapse + fade animation and light blue theme."""
        container = QWidget(parent)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(2)

        toggle = QToolButton(container)
        toggle.setText(title)
        toggle.setCheckable(True)
        toggle.setChecked(False)
        toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        toggle.setArrowType(Qt.ArrowType.RightArrow)
        toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        toggle.setStyleSheet(styles.hfptoggle_stylesheet)
        content = QGroupBox(container)
        content.setLayout(inner_layout)
        content.setMaximumHeight(0)
        content.setWindowOpacity(0.0)
        content.setVisible(False)
        content.setStyleSheet(styles.content_stylesheet)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 2)
        content.setGraphicsEffect(shadow)

        height_anim = QPropertyAnimation(content, b"maximumHeight")
        height_anim.setDuration(250)
        height_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        fade_anim = QPropertyAnimation(content, b"windowOpacity")
        fade_anim.setDuration(250)
        fade_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        animation_group = QParallelAnimationGroup()
        animation_group.addAnimation(height_anim)
        animation_group.addAnimation(fade_anim)
        self.hfp_sections.append(toggle)

        def toggle_section(checked):
            if self.current_expanded_section and self.current_expanded_section != content:
                prev_content = self.current_expanded_section
                prev_height_anim = QPropertyAnimation(prev_content, b"maximumHeight")
                prev_fade_anim = QPropertyAnimation(prev_content, b"windowOpacity")
                prev_height_anim.setDuration(250)
                prev_fade_anim.setDuration(250)
                prev_height_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
                prev_fade_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

                prev_height_anim.setStartValue(prev_content.height())
                prev_height_anim.setEndValue(0)
                prev_fade_anim.setStartValue(1.0)
                prev_fade_anim.setEndValue(0.0)

                def hide_after():
                    prev_content.setVisible(True)
                    animation_group.finished.disconnect(hide_after)

                #animation_group.finished.connect(hide_after)
                animation_group.start()

            if checked:
                content.setVisible(True)
                height_anim.setStartValue(0)
                height_anim.setEndValue(content.sizeHint().height())
                fade_anim.setStartValue(0.0)
                fade_anim.setEndValue(1.0)
                toggle.setArrowType(Qt.ArrowType.DownArrow)
                animation_group.start()
                self.current_expanded_section = content
            else:
                height_anim.setStartValue(content.height())
                height_anim.setEndValue(0)
                fade_anim.setStartValue(1.0)
                fade_anim.setEndValue(0.0)
                toggle.setArrowType(Qt.ArrowType.RightArrow)

                def hide_after():
                    content.setVisible(False)
                    animation_group.finished.disconnect(hide_after)

                animation_group.finished.connect(hide_after)
                animation_group.start()

                self.current_expanded_section = None

        toggle.toggled.connect(toggle_section)

        container_layout.addWidget(toggle)
        container_layout.addWidget(content)
        return container

