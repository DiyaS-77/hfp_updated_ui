# --- Advanced call handling buttons with memory input ---
adv_layout = QVBoxLayout()
self.swap_calls_btn = QPushButton("Swap Calls", widget)
self.hold_answer_btn = QPushButton("Hold + Answer", widget)
self.release_answer_btn = QPushButton("Release + Answer", widget)
self.private_chat_btn = QPushButton("Private Chat", widget)
self.create_multiparty_btn = QPushButton("Create Multiparty", widget)
self.hangup_multiparty_btn = QPushButton("Hangup Multiparty", widget)
self.transfer_calls_btn = QPushButton("Transfer Calls", widget)

# Memory dial controls
memory_layout = QHBoxLayout()
self.memory_input = QSpinBox(widget)
self.memory_input.setRange(1, 9)
self.memory_input.setPrefix("Memory #")
self.dial_memory_btn = QPushButton("Dial Memory", widget)
memory_layout.addWidget(self.memory_input)
memory_layout.addWidget(self.dial_memory_btn)

for b in [self.swap_calls_btn, self.hold_answer_btn, self.release_answer_btn,
          self.private_chat_btn, self.create_multiparty_btn, self.hangup_multiparty_btn,
          self.transfer_calls_btn]:
    adv_layout.addWidget(b)
adv_layout.addLayout(memory_layout)

adv_group = self.create_hfp_sections("Advanced Call Handling", adv_layout, parent=widget)
