# CICIDS2017 Global Dataset Inventory

Generated: 2026-08-16

## 1. Inventory Summary Table

| Dataset | Rows | Columns | Classes | Total NaN | Total Inf | Duplicate Rows (%) | Constant Features | Validation Gate |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv` | 225,745 | 79 | 2 | 4 | 64 | 2,633 (1.17%) | 10 | **WARNING** |
| `Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv` | 286,467 | 79 | 2 | 15 | 727 | 72,353 (25.26%) | 10 | **WARNING** |
| `Friday-WorkingHours-Morning.pcap_ISCX.csv` | 191,033 | 79 | 2 | 28 | 216 | 6,888 (3.61%) | 10 | **WARNING** |
| `Monday-WorkingHours.pcap_ISCX.csv` | 529,918 | 79 | 1 | 64 | 810 | 26,935 (5.08%) | 11 | **WARNING** |
| `Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv` | 288,602 | 79 | 2 | 18 | 396 | 35,630 (12.35%) | 8 | **WARNING** |
| `Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv` | 170,366 | 79 | 4 | 20 | 250 | 6,066 (3.56%) | 10 | **WARNING** |
| `Tuesday-WorkingHours.pcap_ISCX.csv` | 445,909 | 79 | 3 | 201 | 327 | 24,065 (5.4%) | 10 | **WARNING** |
| `Wednesday-workingHours.pcap_ISCX.csv` | 692,703 | 79 | 6 | 1,008 | 1,586 | 81,909 (11.82%) | 10 | **WARNING** |

## 2. Detailed Label Breakdown per Dataset

### `Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv`
| Class Label | Raw Representation | Hex Bytes | Flow Count | Percentage |
| :--- | :--- | :--- | :--- | :--- |
| `DDoS` | `'DDoS'` | `44446f53` | 128,027 | 56.7131% |
| `BENIGN` | `'BENIGN'` | `42454e49474e` | 97,718 | 43.2869% |

### `Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv`
| Class Label | Raw Representation | Hex Bytes | Flow Count | Percentage |
| :--- | :--- | :--- | :--- | :--- |
| `PortScan` | `'PortScan'` | `506f72745363616e` | 158,930 | 55.4793% |
| `BENIGN` | `'BENIGN'` | `42454e49474e` | 127,537 | 44.5207% |

### `Friday-WorkingHours-Morning.pcap_ISCX.csv`
| Class Label | Raw Representation | Hex Bytes | Flow Count | Percentage |
| :--- | :--- | :--- | :--- | :--- |
| `BENIGN` | `'BENIGN'` | `42454e49474e` | 189,067 | 98.9709% |
| `Bot` | `'Bot'` | `426f74` | 1,966 | 1.0291% |

### `Monday-WorkingHours.pcap_ISCX.csv`
| Class Label | Raw Representation | Hex Bytes | Flow Count | Percentage |
| :--- | :--- | :--- | :--- | :--- |
| `BENIGN` | `'BENIGN'` | `42454e49474e` | 529,918 | 100.0% |

### `Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv`
| Class Label | Raw Representation | Hex Bytes | Flow Count | Percentage |
| :--- | :--- | :--- | :--- | :--- |
| `BENIGN` | `'BENIGN'` | `42454e49474e` | 288,566 | 99.9875% |
| `Infiltration` | `'Infiltration'` | `496e66696c74726174696f6e` | 36 | 0.0125% |

### `Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv`
| Class Label | Raw Representation | Hex Bytes | Flow Count | Percentage |
| :--- | :--- | :--- | :--- | :--- |
| `BENIGN` | `'BENIGN'` | `42454e49474e` | 168,186 | 98.7204% |
| `Web Attack ï¿½ Brute Force` | `'Web Attack ï¿½ Brute Force'` | `5765622041747461636b20efbfbd20427275746520466f726365` | 1,507 | 0.8846% |
| `Web Attack ï¿½ XSS` | `'Web Attack ï¿½ XSS'` | `5765622041747461636b20efbfbd20585353` | 652 | 0.3827% |
| `Web Attack ï¿½ Sql Injection` | `'Web Attack ï¿½ Sql Injection'` | `5765622041747461636b20efbfbd2053716c20496e6a656374696f6e` | 21 | 0.0123% |

### `Tuesday-WorkingHours.pcap_ISCX.csv`
| Class Label | Raw Representation | Hex Bytes | Flow Count | Percentage |
| :--- | :--- | :--- | :--- | :--- |
| `BENIGN` | `'BENIGN'` | `42454e49474e` | 432,074 | 96.8973% |
| `FTP-Patator` | `'FTP-Patator'` | `4654502d50617461746f72` | 7,938 | 1.7802% |
| `SSH-Patator` | `'SSH-Patator'` | `5353482d50617461746f72` | 5,897 | 1.3225% |

### `Wednesday-workingHours.pcap_ISCX.csv`
| Class Label | Raw Representation | Hex Bytes | Flow Count | Percentage |
| :--- | :--- | :--- | :--- | :--- |
| `BENIGN` | `'BENIGN'` | `42454e49474e` | 440,031 | 63.5238% |
| `DoS Hulk` | `'DoS Hulk'` | `446f532048756c6b` | 231,073 | 33.3582% |
| `DoS GoldenEye` | `'DoS GoldenEye'` | `446f5320476f6c64656e457965` | 10,293 | 1.4859% |
| `DoS slowloris` | `'DoS slowloris'` | `446f5320736c6f776c6f726973` | 5,796 | 0.8367% |
| `DoS Slowhttptest` | `'DoS Slowhttptest'` | `446f5320536c6f776874747074657374` | 5,499 | 0.7938% |
| `Heartbleed` | `'Heartbleed'` | `4865617274626c656564` | 11 | 0.0016% |

