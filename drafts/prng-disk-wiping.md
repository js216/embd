```
jk@Tulien:~/projects/rand$ time ./rand | sudo dd of=/dev/sdc status=progress
4000752517632 bytes (4.0 TB, 3.6 TiB) copied, 841950 s, 4.8 MB/s
dd: writing to '/dev/sdc': No space left on device
7813969921+0 records in
7813969920+0 records out
4000752599040 bytes (4.0 TB, 3.6 TiB) copied, 841950 s, 4.8 MB/s

real    14032m30.197s
user    1179m12.489s
sys     547m4.609s
```

```
jk@Tulien:~/projects/rand$ time ./rand | dd status=progress | sudo cmp /dev/sdc -
4000750588416 bytes (4.0 TB, 3.6 TiB) copied, 147943 s, 27.0 MB/scmp: EOF on /dev/sdc after byte 4000752599040, in line 15627921233

real    2465m44.887s
user    1591m45.277s
sys     807m29.837s
```
