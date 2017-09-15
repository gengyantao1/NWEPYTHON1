import  time,sys
for i in range(5):
    print i
    time.sleep(2)
    try:
        sys.stdout.flush('h')
    except Exception as e:
        print e
