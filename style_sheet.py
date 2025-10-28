back_button_style_sheet = """QPushButton {
                                font-size: 16px;
                                padding: 6px;
                                background-color: black;
                                color: white;
                                border: 2px solid gray;
                                border-radius: 6px;
                          }
                            QPushButton:hover {
                                background-color: #333333;
                          }"""


bluetooth_profiles_button_style = """QPushButton {
                                        background-color: QLinearGradient(
                                        spread:reflect, x1:0, y1:0, x2:1, y2:0,
                                        stop:0 #e0f7fa, stop:1 #b2ebf2
                                        );
                                        border: 1px solid #81d4fa;
                                        border-radius: 6px;
                                        color: #006064;
                                        padding: 6px 10px;
                                        font-weight: bold;
                                    }

                                        QPushButton:hover {
                                            background-color: QLinearGradient(
                                                spread:pad, x1:0, y1:0, x2:1, y2:0,
                                                stop:0 #b2ebf2, stop:1 #4dd0e1
                                            );
                                        }

                                        QPushButton:pressed {
                                            background-color: #4dd0e1;
                                        }
                                        """


bluetooth_profiles_groupbox_style = """QGroupBox {
                                            font-weight: bold;
                                            border: 1px solid #ccc;
                                            border-radius: 5px;
                                            margin-top: 12px;
                                    }
                                        QGroupBox::title {
                                            subcontrol-origin: margin;
                                            left: 10px;
                                            padding: 0 4px 0 4px;
                                    }"""


color_style_sheet = """QLabel#PairedDevicesList, QLabel#ControllerDetails  {
                            color: black;
                            margin-bottom: 6px;
                        }

                        QLabel#label_widget, QLabel#value_widget, QLabel#DumpLogs, QLabel#InquiryTimeoutLabel, QLabel#profile_description_label,
                        QPushButton#PairButton, QPushButton#ConnectButton{
                            color: black;
                        }                  

                        QLabel#WarningLabel, QPushButton#SetDiscoverableOffButton, QPushButton#StopButton, QPushButton#SetDiscoveryOffButton {
                            color: red;
                        }            

                        QLabel#SetDiscoverable, QLabel#Inquiry, QLabel#DiscoverableTimeout, QPushButton#RefreshButton, QPushButton#RegisterAgent,
                        QPushButton#SetDiscoveryOnButton, QPushButton#UnregisterAgent{
                            color: blue;
                        }         

                        QPushButton#StartButton, QPushButton#SetDiscoverableOnButton {
                            color: green;
                        }"""


controllers_list_widget_style_sheet = """QListWidget{ 
				                            font: 14pt "Arial"; 
                                            color: black; background: 
                                            transparent; padding: 5px; 
                                            } 
                                         QListWidget::item { 
                                            padding : 5px;
                                            border: 2px solid black; 
                                         } 
                                        QListWidget::item:selected {
                                            background-color:white; 
                                            color: black; }"""


cmd_list_widget_style_sheet = """ QTreeWidget {
                                    font: 12pt "Arial";
                                    color: black;
                                    background: transparent;
                                    padding: 2px;
                                    border: 2px solid black;
                                }
                                QListWidget::item {
                                    padding : 2px;
                                    border: 2px solid black;
                                }
                                QListWidget::item:selected {
                                    background-color: white;
                                    color: black;
                                }"""


device_button_style_sheet = """ QToolButton {
                                    font: 11pt "Arial";
                                    color: white;
                                    background: transparent;
                                    padding: 10px;
                                }
                                QToolButton:hover {
                                    background-color: transparent;
                                }"""


device_tab_widget_style_sheet = """background-color: lightblue; color: black;"""


dump_logs_output_style_sheet = """QTextEdit{
                        background: transparent;
                        color: black;
                        border: 2px solid black;
                        }"""


dump_logs_style_sheet = """QLabel{
                        border: 2px solid black; 
                        color: black; 
                        font-size:18px; 
                        font-weight: bold;
                        }"""


execute_button_style_sheet = """QPushButton{
                                font-size: 18px; 
                                color: white; 
                                background: transparent; 
                                padding: 10px;
                             }"""


gap_button_style_sheet = """QPushButton {
                                color: black;
                                background-color: rgba(204, 229, 255, 0.6);
                                border: 1px solid rgba(0, 0, 0, 0.2);
                                border-radius: 8px;
                                padding: 6px 14px;
                            }
                         QPushButton:hover {
                                background-color: rgba(179, 218, 255, 0.7);
                         }"""


horizontal_header_style_sheet = """QHeaderView::section {
                                    background-color: #f0f0f0;
                                    color: black;
                                    font-weight: bold;
                                    padding: 4px;
                                }"""


input_layout_style_sheet = """QListWidget{
                        background: transparent; 
                        border: 2px solid black; 
                        }"""


middle_panel_style_sheet = """QWidget#ProfileContainer {
                                background-color: rgba(255, 255, 255, 0.12);
                                border: 1px solid rgba(0, 0, 0, 0.2);
                                border-radius: 10px;
                                }"""


panel_style_sheet = """background-color: rgba(255,255,255,0.12);
                        border: 1px solid rgba(0,0,0,0.2);
                        border-radius: 10px;
                        padding: 8px;"""


profiles_list_style_sheet = """QListWidget {
                                    background-color: transparent;
                                    border: none;
                                    color: black;
                                }
                               QListWidget::item {
                                    padding: 4px;
                                    margin: 2px 0;
                                }
                               QListWidget::item:selected {
                                    background-color: rgba(0, 120, 215, 0.15);
                                    border-radius: 6px;
                                    color: black;
                               }"""


reset_button_style_sheet = """QPushButton{
                           font-size: 18px; 
                           color: white; 
                           background: transparent; 
                           padding: 10px;
                           }"""


select_button_style_sheet = """ QToolButton {
                                    font-size: 20px;
                                    color: white;
                                    background: transparent;
                                    padding: 20px;
                                }
                                QToolButton:hover {
                                    background-color: transparent;
                                }"""


vertical_header_style_sheet = """QHeaderView::section {
                                    background-color: #f0f0f0;
                                    color: black;
                                    font-weight: bold;
                                    padding: 4px;
                                }"""

tab_style_sheet = """QTabWidget::pane {
                                    background-color: rgba(255,255,255,0.12);
                                    border: 1px solid rgba(0,0,0,0.2);
                                    border-radius: 10px;
                                    padding: 8px;
                                 }
                                 QTabBar::tab {
                                    background-color: rgba(255,255,255,0.12);
                                    border: 1px solid rgba(0,0,0,0.2);
                                    border-radius: 8px;
                                    padding: 6px 12px;
                                    margin: 2px;
                                    color: black;
                                 }
                                 QTabBar::tab:selected {
                                    background-color: rgba(255,255,255,0.3);
                                    font-weight: bold;
                                 }
                                 QTabBar::tab:hover {
                                    background-color: rgba(255,255,255,0.2);
                                 }"""

transparent_textedit_style = """QTextEdit {
                                    background: transparent;
                                    color: black;
                                    border: none;
                                }"""


progress_slider_style_sheet = """QSlider::groove:horizontal {
                                    border: 1px solid #999999;
                                    height: 6px;
                                    background: #e0e0e0;
                                    border-radius: 3px;
                                }                              
                                QSlider::sub-page:horizontal {
                                    background: #3b82f6; 
                                    border: 1px solid #777;
                                    height: 6px;
                                    border-radius: 3px;
                                }                               
                                QSlider::add-page:horizontal {
                                    background: #d0d0d0;
                                    border: 1px solid #777;
                                    height: 6px;
                                    border-radius: 3px;
                                }                              
                                QSlider::handle:horizontal {
                                    background: #ffffff;
                                    border: 1px solid #3b82f6;
                                    width: 14px;
                                    height: 14px;
                                    margin: -5px 0;  
                                    border-radius: 7px;
                                }
                                QSlider::handle:horizontal:hover {
                                    background: #3b82f6;
                                    border: 1px solid #1e40af;
                                }
                                """


widget_style_sheet ="""QGroupBox {
                            border: 1px solid #a0a0a0;
                            border-radius: 6px;
                            margin-top: 8px;
                        }
                        QPushButton {
                            background-color: #6ea8fe;
                            color: white;
                            border-radius: 4px;
                        }
                        QPushButton:hover {
                            background-color: #2e8bff;
                        }
                        QToolButton {
                            font-size: 13px;
                        }
                        """


volume_slider_style_sheet = """QSlider::groove:horizontal {
                                border: 1px solid #999999;
                                height: 6px;
                                background: #cccccc;
                                border-radius: 3px;
                            }                                
                                QSlider::sub-page:horizontal {
                                    background: #4caf50;  /* green progress */
                                    border: 1px solid #777;
                                    height: 6px;
                                    border-radius: 3px;
                                }                                
                                QSlider::add-page:horizontal {
                                    background: #e0e0e0;
                                    border: 1px solid #777;
                                    height: 6px;
                                    border-radius: 3px;
                                }                                
                                QSlider::handle:horizontal {
                                    background: #ffffff;
                                    border: 1px solid #4caf50;
                                    width: 14px;
                                    height: 14px;
                                    margin: -5px 0;  /* center the handle */
                                    border-radius: 7px;
                                }                                
                                QSlider::handle:horizontal:hover {
                                    background: #4caf50;
                                    border: 1px solid #2e7d32;
                                    }"""
