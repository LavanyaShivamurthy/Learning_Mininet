#Learning _Mininet

Fileystem 

1. Run command  --> sh RunCode.sh 
	This will clean up all previous mininet runing if any
	then starts BaseCode_Mqtt_Collector.py

2. BaseCode_Mqtt_Collector.py        exectes 
	2.1. sensor_subscriber.py
	2.2. sensor_publisher.py

3.Scipts required to extract to csv file         



Run command --->  python3 extract_and_merge_with_summary.py
this will call mqtt_extract_and_validate_all.sh


	PCAP_DIR/
	 ├── s1.pcap
	 ├── s2.pcap
	 ├── s3.pcap
        ↓
mqtt_extract_and_validate_all.sh (called once per PCAP)
        ↓
csv_output/
	 ├── s1_extracted.csv
	 ├── s2_extracted.csv
	 ├── s3_extracted.csv
        ↓
  merge_and_clean_csvs()
        ↓
 all_labeled_data_clean.csv  (still unlabeled, name can change later)


