A simple stock screener that uses Mark Minervini's trend template, and other indicators on stocks on Oslo stock exchange

The script can be run without any inputs, it will then save to local sqliteDB and print to terminal.  
Or it can be run directly with docker.

```
docker run enzanto/stockfinder:latest
```

Provide webhook URL from discord to make it post to discord channel

connect to seperate DB with ENV variables.

ENV Variables:

- dicord_url  
- DBUSER  
- DBPASSWORD  
- DBADDRESS  
- DBNAME  
- DBPORT  

credits:  
Big thanks to Richard Moglen for giving me both the idea of making this, and great guides to both python and stock market in general.
https://twitter.com/RichardMoglen  
https://www.youtube.com/@RichardMoglen

Also big thanks to Mr Algovibes on youtube for having some great ideas and tutorials.  
https://www.youtube.com/@Algovibes