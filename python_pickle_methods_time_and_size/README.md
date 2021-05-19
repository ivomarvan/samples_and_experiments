# Test time and size pickle methods
It tests different data storage methods (_feather, sql, csv, hdf, pickle, parquet_) 
for different types (_gzip, bz2, zip, xz_) 
and compression levels (_0-9_).

**Measures read/write times and size for a given number of experiments (parameter -e) on a test file (parameter -i).**

The results score and display a table of winning technologies where the best features are a compromise between 
the times of reading, writing and size on the disk.

If you want to test a special data type (with indexes, converting values ​​to times, etc.), edit the read_sample_data function.

**Attention, testing on your computer with your python libraries can be time-consuming!**

Command line arguments:

  -h, --help 
             
        show the help message and exit
  
  -i <infile>, --infile <infile>
  
        input gziped csv file with test data
        (default:./data/in/data.csv.gz)
  
  -od <outdir>, --outdir <outdir>
  
        output directory for result (default:./data/out)
  
  -e <number_of_experiments>, --number_of_experiments <number_of_experiments>
  
        number of experiments for avarage for one methode
---------------------
Running on my enviroment:
time python3 time_size_read_write.py -e 5

real	6m39,581s

user	6m1,689s

sys	0m15,497s

--------------------------------------------------------------------------------

Master for "write_time":        \['pickle.protocol_3.compression_None']

Master for "read_time":         \['pickle.protocol_3.compression_None']

Master for "size":              \['pickle.protocol_4.compression_xz']

Master of compromise:           \['parquet.engine_auto.compression_snappy']

--------------------------------------------------------------------------------

All results you can find in directory **data/out**.

You can open **data/out/results.csv** in spreadsheet.

