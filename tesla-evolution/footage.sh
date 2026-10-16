#!/bin/sh
# Usage: ./footage.sh source.mp4 foot.mp4
# 取 14.58s 起 0.88s 的起飞镜头：遮掉台标，跟踪裁剪车身，水平镜像（车头朝右），慢放 3 倍并补帧到 60fps
ffmpeg -v error -y -ss 14.58 -t 0.88 -i "$1" -vf "setpts=PTS-STARTPTS,delogo=x=588:y=586:w=100:h=100,crop=680:382:30:'if(lt(t,0.11),775+(740-775)*(t-0)/0.110,if(lt(t,0.27),740+(617-740)*(t-0.11)/0.160,if(lt(t,0.44),617+(520-617)*(t-0.27)/0.170,if(lt(t,0.61),520+(454-520)*(t-0.44)/0.170,if(lt(t,0.77),454+(416-454)*(t-0.61)/0.160,if(lt(t,0.89),416+(380-416)*(t-0.77)/0.120,380))))))',scale=1920:1080:flags=lanczos,hflip,setpts=3*PTS,minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:vsbmc=1,unsharp=5:5:0.6,eq=contrast=1.06:saturation=1.05" -an -c:v libx264 -crf 10 -preset slow -pix_fmt yuv420p "$2"
