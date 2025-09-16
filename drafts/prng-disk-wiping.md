```
jk@Tulien:~/projects/rand$ time ./rand | sudo dd of=/dev/sdc status=progress
4000752517632 bytes (4.0 TB, 3.6 TiB) copied, 841950 s, 4.8 MB/s^[[1;5A
dd: writing to '/dev/sdc': No space left on device
7813969921+0 records in
7813969920+0 records out
4000752599040 bytes (4.0 TB, 3.6 TiB) copied, 841950 s, 4.8 MB/s

real    14032m30.197s
user    1179m12.489s
sys     547m4.609s
jk@Tulien:~/projects/rand$
```


