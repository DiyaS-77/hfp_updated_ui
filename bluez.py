def swap_calls(self, device_address):
    """Swap Active and Held calls on the device."""
    path = self.get_ofono_modem_path(device_address)
    if not path:
        self.log.warning(f"No ofono modem path for {device_address}")
        return False
    try:
        voice_call_manager = dbus.Interface(self.bus.get_object("org.ofono", path),
                                            "org.ofono.VoiceCallManager")
        voice_call_manager.SwapCalls()
        self.log.info(f"Swapped calls on {device_address}")
        return True
    except Exception as error:
        self.log.error(f"Failed to swap calls on {device_address}: {error}")
        return False

def dial_memory(self, device_address, memory_position, hide_callerid="default"):
    """Initiates a call to a number stored in memory/favorite.

    Args:
        device_address: Bluetooth address of remote device.
        memory_position: Memory position/favorite to dial.
        hide_callerid: whether to hide caller ID or not.
    """
    path = self.get_ofono_modem_path(device_address)
    if not path:
        self.log.warning(f"No ofono modem path for {device_address}")
        return False
    try:
        voice_call_manager = dbus.Interface(self.bus.get_object("org.ofono", path),
                                            "org.ofono.VoiceCallManager")
        call_path = voice_call_manager.DialMemory(memory_position, hide_callerid)
        self.log.info(f"Dialed memory position {memory_position} on {device_address}, call path: {call_path}")
        return call_path
    except Exception as error:
        self.log.error(f"Failed to dial memory on {device_address}: {error}")
        return False


def transfer_calls(self, device_address):
    """Transfer active and held calls."""
    path = self.get_ofono_modem_path(device_address)
    if not path:
        self.log.warning(f"No ofono modem path for {device_address}")
        return False
    try:
        voice_call_manager = dbus.Interface(self.bus.get_object("org.ofono", path),
                                            "org.ofono.VoiceCallManager")
        voice_call_manager.Transfer()
        self.log.info(f"Transferred calls on {device_address}")
        return True
    except Exception as error:
        self.log.error(f"Failed to transfer calls on {device_address}: {error}")
        return False


def release_and_answer(self, device_address):
    """Release active call(s) and answer waiting call."""
    path = self.get_ofono_modem_path(device_address)
    if not path:
        self.log.warning(f"No ofono modem path for {device_address}")
        return False
    try:
        voice_call_manager = dbus.Interface(self.bus.get_object("org.ofono", path),
                                            "org.ofono.VoiceCallManager")
        voice_call_manager.ReleaseAndAnswer()
        self.log.info(f"Released active calls and answered waiting call on {device_address}")
        return True
    except Exception as error:
        self.log.error(f"Failed to release and answer call on {device_address}: {error}")
        return False


def release_and_swap(self, device_address):
    """Release active call(s) and activate held call(s)."""
    path = self.get_ofono_modem_path(device_address)
    if not path:
        self.log.warning(f"No ofono modem path for {device_address}")
        return False
    try:
        voice_call_manager = dbus.Interface(self.bus.get_object("org.ofono", path),
                                            "org.ofono.VoiceCallManager")
        voice_call_manager.ReleaseAndSwap()
        self.log.info(f"Released active calls and swapped held calls on {device_address}")
        return True
    except Exception as error:
        self.log.error(f"Failed to release and swap calls on {device_address}: {error}")
        return False


def hold_and_answer(self, device_address):
    """Hold active call(s) and answer waiting call."""
    path = self.get_ofono_modem_path(device_address)
    if not path:
        self.log.warning(f"No ofono modem path for {device_address}")
        return False
    try:
        voice_call_manager = dbus.Interface(self.bus.get_object("org.ofono", path),
                                            "org.ofono.VoiceCallManager")
        voice_call_manager.HoldAndAnswer()
        self.log.info(f"Held active calls and answered waiting call on {device_address}")
        return True
    except Exception as error:
        self.log.error(f"Failed to hold and answer call on {device_address}: {error}")
        return False


def private_chat(self, device_address, call_path):
    """Place multiparty call on hold and activate selected call.

    Args:
        device_address: Bluetooth address of remote device.
        call_path: Path of the call to make active.
    Returns:
        List of call paths participating in multiparty call.
    """
    path = self.get_ofono_modem_path(device_address)
    if not path:
        self.log.warning(f"No ofono modem path for {device_address}")
        return []
    try:
        voice_call_manager = dbus.Interface(self.bus.get_object("org.ofono", path),
                                            "org.ofono.VoiceCallManager")
        new_call_list = voice_call_manager.PrivateChat(call_path)
        self.log.info(f"Private chat activated for call {call_path} on {device_address}")
        return new_call_list
    except Exception as error:
        self.log.error(f"Failed to start private chat on {device_address}: {error}")
        return []


def create_multiparty(self, device_address):
    """Join active and held calls into a multiparty call."""
    path = self.get_ofono_modem_path(device_address)
    if not path:
        self.log.warning(f"No ofono modem path for {device_address}")
        return []
    try:
        voice_call_manager = dbus.Interface(self.bus.get_object("org.ofono", path),
                                            "org.ofono.VoiceCallManager")
        multiparty_calls = voice_call_manager.CreateMultiparty()
        self.log.info(f"Multiparty call created on {device_address}, calls: {multiparty_calls}")
        return multiparty_calls
    except Exception as error:
        self.log.error(f"Failed to create multiparty call on {device_address}: {error}")
        return []


def hangup_multiparty(self, device_address):
    """Hang up the multiparty call."""
    path = self.get_ofono_modem_path(device_address)
    if not path:
        self.log.warning(f"No ofono modem path for {device_address}")
        return False
    try:
        voice_call_manager = dbus.Interface(self.bus.get_object("org.ofono", path),
                                            "org.ofono.VoiceCallManager")
        voice_call_manager.HangupMultiparty()
        self.log.info(f"Multiparty call hung up on {device_address}")
        return True
    except Exception as error:
        self.log.error(f"Failed to hang up multiparty call on {device_address}: {error}")
        return False


def send_tones(self, device_address, tones):
    """Send DTMF tones over active call.

    Args:
        device_address: Bluetooth address of remote device.
        tones: String of DTMF tones (0-9, *, #, A-D)
    """
    path = self.get_ofono_modem_path(device_address)
    if not path:
        self.log.warning(f"No ofono modem path for {device_address}")
        return False
    try:
        voice_call_manager = dbus.Interface(self.bus.get_object("org.ofono", path),
                                            "org.ofono.VoiceCallManager")
        voice_call_manager.SendTones(tones)
        self.log.info(f"Sent tones '{tones}' on {device_address}")
        return True
    except Exception as error:
        self.log.error(f"Failed to send tones on {device_address}: {error}")
        return False
