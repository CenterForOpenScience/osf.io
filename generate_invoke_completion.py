def main():
    f = open('tasks.py', 'r')
    tasks = []
    lines = f.read().split('\n')
    f.close()
    for i in range(len(lines)):
        line = lines[i]
        if '@task' in line:
            opt = lines[i + 1].replace('def ', '').split('(')[0]
            tasks.append(opt)
    templ = open('.invoke_completion_template', 'r').read()
    templ = templ.replace('__OPTS__', ' '.join(tasks))
    out = open('.invoke_completion.sh', 'wb')
    out.write(templ)
    out.close()

if __name__ == "__main__":
    main()
