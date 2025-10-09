### 4 TB

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

### 5 TB

```
jk@Tulien:~/projects/rand$ time ./rand | sudo dd of=/dev/sdc status=progress
[sudo] password for jk:
5000944067072 bytes (5.0 TB, 4.5 TiB) copied, 1285556 s, 3.9 MB/s
dd: writing to '/dev/sdc': No space left on device
9767475201+0 records in
9767475200+0 records out
5000947302400 bytes (5.0 TB, 4.5 TiB) copied, 1.28556e+06 s, 3.9 MB/s

real    21426m4.788s
user    2029m39.804s
sys     872m51.606s
```

```
jk@Tulien:~/projects/rand$ time ./rand | dd status=progress | sudo cmp /dev/sdc -
[sudo] password for jk:
1639330622976 bytes (1.6 TB, 1.5 TiB) copied, 49184 s, 33.3 MB/s/dev/sdc - differ: byte 1639355379713, line 6403618061

real    819m46.517s
user    529m6.439s
sys     260m34.082s
jk@Tulien:~/projects/rand$
```
